from itertools import islice

from jsonforge.core.casting import parse_preserving_type, parse_typed_value
from jsonforge.core.document import ConcurrentModificationError, JsonDocument
from jsonforge.core.embedded_json import decode_if_embedded_json
from jsonforge.core.paths import (
    JsonPath,
    add_path,
    delete_path,
    format_value,
    get_path,
    iter_paths,
    set_path,
)
from jsonforge.core.search import search

from .prompts import ask, ask_with_path_completions, choose
from .render import (
    render_change_preview,
    render_container_children,
    render_path_summary,
    render_search_results,
    render_status,
)

VALUE_TYPES = ["preserve", "auto", "string", "int", "float", "bool", "null", "json"]
SEARCH_SCOPES = ["all", "key", "value", "path"]


def ask_non_negative_int(label: str, default: int) -> int:
    raw_value = ask(label).strip()
    if not raw_value:
        return default
    value = int(raw_value)
    if value < 0:
        raise ValueError("Value must be greater than or equal to 0")
    return value


def ask_yes_no(label: str, *, default: bool = False) -> bool:
    answer = ask(label).strip().lower()
    if not answer:
        return default
    return answer.startswith("y")


def json_type_name(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def preview_value(value, limit: int = 120) -> str:
    if limit < 3:
        raise ValueError("Preview must be greater than or equal to 3")
    if isinstance(value, dict):
        label = "entry" if len(value) == 1 else "entries"
        return f"{{...}} ({len(value)} {label})"
    if isinstance(value, list):
        label = "entry" if len(value) == 1 else "entries"
        return f"[...] ({len(value)} {label})"
    rendered = format_value(value).replace("\n", " ")
    if len(rendered) > limit:
        return rendered[: limit - 3] + "..."
    return rendered


def same_json_value(left, right) -> bool:
    stack = [(left, right)]
    while stack:
        current_left, current_right = stack.pop()
        if type(current_left) is not type(current_right):
            return False
        if isinstance(current_left, dict):
            if current_left.keys() != current_right.keys():
                return False
            stack.extend((current_left[key], current_right[key]) for key in current_left)
        elif isinstance(current_left, list):
            if len(current_left) != len(current_right):
                return False
            stack.extend(zip(current_left, current_right, strict=True))
        elif current_left != current_right:
            return False
    return True


def display_path(path: JsonPath) -> str:
    try:
        return path.to_dot()
    except ValueError:
        return path.to_pointer()


def contains_embedded_json(data) -> bool:
    stack = [data]
    while stack:
        current = stack.pop()
        decoded = decode_if_embedded_json(current, enabled=True)
        if decoded.was_embedded_json:
            return True
        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False


def embedded_storage_path(data, path: JsonPath) -> str | None:
    root = decode_if_embedded_json(data, enabled=True)
    if root.was_embedded_json:
        return "<root>"
    for length in range(1, len(path.parts) + 1):
        prefix = JsonPath(path.parts[:length])
        try:
            raw_value = get_path(data, prefix).value
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        if decode_if_embedded_json(raw_value, enabled=True).was_embedded_json:
            return display_path(prefix)
    return None


def prompt_scalar_value(current):
    current_type = json_type_name(current)
    while True:
        raw_value = ask(f"New value [{current_type}] (:type to change type): ")
        if raw_value.strip().lower() == ":type":
            value_type = choose(
                "New type (auto/string/int/float/bool/null/json): ",
                VALUE_TYPES[1:],
            )
            return parse_typed_value(ask("New value: "), value_type)
        try:
            return parse_preserving_type(raw_value, current)
        except ValueError as exc:
            render_status(str(exc), kind="error")
            action = choose(
                "Correct value, change type, or cancel (1/2/3): ",
                ["1", "2", "3"],
            )
            if action == "2":
                value_type = choose(
                    "New type (auto/string/int/float/bool/null/json): ",
                    VALUE_TYPES[1:],
                )
                return parse_typed_value(ask("New value: "), value_type)
            if action == "3":
                return current


def _container_children(current, query: str):
    children = current.keys() if isinstance(current, dict) else range(len(current))
    if not query:
        return children, len(current)
    filtered = [child for child in children if query.lower() in str(child).lower()]
    return filtered, len(filtered)


def edit_path_guided(doc: JsonDocument, path: str | JsonPath, *, decode_embedded: bool) -> bool:
    selected = JsonPath.from_dot(path) if isinstance(path, str) else path

    while True:
        match = get_path(doc.data, selected, decode_embedded=decode_embedded)
        current = match.value
        current_type = json_type_name(current)
        rendered_path = display_path(selected)
        storage_path = embedded_storage_path(doc.data, selected) if decode_embedded else None
        storage = f'embedded JSON within "{storage_path}"' if storage_path is not None else None
        render_path_summary(
            rendered_path,
            current_type,
            storage=storage,
            child_count=len(current) if isinstance(current, (dict, list)) else None,
            current_value=None if isinstance(current, (dict, list)) else format_value(current),
        )

        if isinstance(current, (dict, list)):
            page = 0
            query = ""
            while True:
                all_children, filtered_count = _container_children(current, query)
                page_count = max(1, (filtered_count + 49) // 50)
                page = min(page, page_count - 1)
                start = page * 50
                children = list(islice(all_children, start, start + 50))
                rows = []
                for index, child in enumerate(children, start=1):
                    child_value = current[child]
                    child_value = decode_if_embedded_json(
                        child_value,
                        enabled=decode_embedded,
                    ).value
                    rows.append(
                        (index, str(child), json_type_name(child_value), preview_value(child_value))
                    )
                caption = f"Page {page + 1}/{page_count}; {filtered_count} entries"
                if query:
                    caption += f'; filter: "{query}"'
                render_container_children(rows, caption=caption)
                action = ask("Select child, N/P page, / filter, R replace, Enter return: ").strip()
                if not action:
                    return False
                if action.lower() == "n":
                    if page + 1 < page_count:
                        page += 1
                    else:
                        render_status("Already on the last page.", kind="warning")
                    continue
                if action.lower() == "p":
                    if page:
                        page -= 1
                    else:
                        render_status("Already on the first page.", kind="warning")
                    continue
                if action == "/":
                    query = ask("Filter immediate children (blank clears): ").strip()
                    page = 0
                    continue
                if action.lower() == "r":
                    value_type = choose(
                        "Replacement type (auto/string/int/float/bool/null/json): ",
                        VALUE_TYPES[1:],
                    )
                    value = parse_typed_value(ask("New value: "), value_type)
                    render_change_preview(
                        rendered_path,
                        preview_value(current),
                        preview_value(value),
                        current_type,
                        json_type_name(value),
                    )
                    expected = f"REPLACE {rendered_path}"
                    if ask(f"Type {expected} to continue: ").strip() != expected:
                        render_status("Update cancelled.", kind="warning")
                        return False
                    if same_json_value(value, current):
                        render_status("No changes to apply.", kind="info")
                        return False
                    doc.data = set_path(
                        doc.data,
                        selected,
                        value,
                        decode_embedded=decode_embedded,
                    )
                    render_status("Updated.", kind="success")
                    return True
                try:
                    child_index = int(action) - 1
                    child = children[child_index]
                    if child_index < 0:
                        raise IndexError
                except (ValueError, IndexError):
                    render_status("Invalid selection.", kind="error")
                    continue
                selected = JsonPath(selected.parts + (str(child),))
                break
            continue

        value = prompt_scalar_value(current)
        if same_json_value(value, current):
            render_status("No changes to apply.", kind="info")
            return False
        render_change_preview(
            rendered_path,
            preview_value(current),
            preview_value(value),
            current_type,
            json_type_name(value),
        )
        if not ask_yes_no("Apply this change? [Y/n]: ", default=True):
            render_status("Update cancelled.", kind="warning")
            return False
        doc.data = set_path(
            doc.data,
            selected,
            value,
            decode_embedded=decode_embedded,
        )
        render_status("Updated.", kind="success")
        return True


def delete_path_guided(
    doc: JsonDocument,
    path: str | JsonPath,
    *,
    decode_embedded: bool,
) -> bool:
    selected = JsonPath.from_dot(path) if isinstance(path, str) else path
    current = get_path(doc.data, selected, decode_embedded=decode_embedded).value
    rendered_path = display_path(selected)
    current_type = json_type_name(current)
    storage_path = embedded_storage_path(doc.data, selected) if decode_embedded else None
    storage = f'embedded JSON within "{storage_path}"' if storage_path is not None else None
    render_path_summary(
        rendered_path,
        current_type,
        storage=storage,
        child_count=len(current) if isinstance(current, (dict, list)) else None,
        current_value=None if isinstance(current, (dict, list)) else format_value(current),
    )
    if isinstance(current, (dict, list)):
        expected = f"DELETE {rendered_path}"
        if (
            ask(f"This removes the entire container. Type {expected} to continue: ").strip()
            != expected
        ):
            render_status("Delete cancelled.", kind="warning")
            return False
    elif not ask_yes_no("Confirm deletion? [y/N]: "):
        render_status("Delete cancelled.", kind="warning")
        return False
    doc.data = delete_path(doc.data, selected, decode_embedded=decode_embedded)
    render_status("Deleted.", kind="success")
    return True


def run_interactive(json_file: str, *, max_bytes: int | None = None) -> None:
    doc = JsonDocument.load(json_file, max_bytes=max_bytes)
    dirty = False
    print(f"JsonForge: {doc.path}")

    while True:
        print("\n--- Main Menu ---")
        print("1) Show root keys")
        print("2) Get value by path")
        print("3) Go directly to a path")
        print("4) Search and edit")
        print("5) Add value by path")
        print("6) Delete path")
        print("7) Tree/list paths")
        print("8) Save with backup")
        print("9) Exit")
        choice = choose("Option: ", ["1", "2", "3", "4", "5", "6", "7", "8", "9"])

        if choice == "1":
            keys = doc.root_keys()
            if not keys:
                print("No root keys; root is a scalar value.")
            for key in keys:
                print(" -", key)
        elif choice == "2":
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            path = ask_with_path_completions("Path: ", doc.data, decode_embedded=decode_embedded)
            try:
                match = get_path(doc.data, path, decode_embedded=decode_embedded)
                selected = JsonPath.from_dot(path)
                value = match.value
                if isinstance(value, (dict, list)):
                    storage_path = (
                        embedded_storage_path(doc.data, selected) if decode_embedded else None
                    )
                    storage = (
                        f'embedded JSON within "{storage_path}"'
                        if storage_path is not None
                        else None
                    )
                    render_path_summary(
                        display_path(selected),
                        json_type_name(value),
                        storage=storage,
                        child_count=len(value),
                        current_value=None,
                    )
                    if ask("V view full JSON, Enter return: ").strip().lower() == "v":
                        print(format_value(value))
                else:
                    print(format_value(value))
                if match.decoded_embedded_segments:
                    print(f"Decoded embedded JSON segments: {match.decoded_embedded_segments}")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "3":
            decode_embedded = contains_embedded_json(doc.data) and ask_yes_no(
                "Embedded JSON detected. Explore its content? [Y/n]: ",
                default=True,
            )
            path = ask_with_path_completions("Path: ", doc.data, decode_embedded=decode_embedded)
            try:
                dirty = (
                    edit_path_guided(
                        doc,
                        path,
                        decode_embedded=decode_embedded,
                    )
                    or dirty
                )
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "4":
            query = ask("Search: ")
            try:
                scope = choose("Search in (all/key/value/path): ", SEARCH_SCOPES)
                exact = ask_yes_no("Require an exact match? [y/N]: ")
                limit = ask_non_negative_int("Limit (blank for 50): ", 50)
                offset = ask_non_negative_int("Offset (blank for 0): ", 0)
                decode_embedded = contains_embedded_json(doc.data) and ask_yes_no(
                    "Embedded JSON detected. Search inside it? [Y/n]: ",
                    default=True,
                )
                matches = list(
                    search(
                        doc.data,
                        query,
                        scope=scope,
                        exact=exact,
                        limit=limit,
                        offset=offset,
                        decode_embedded=decode_embedded,
                    )
                )
                if not matches:
                    render_status("No matches.", kind="warning")
                    continue
                render_search_results(
                    query,
                    [
                        (index, display_path(path), json_type_name(value), preview_value(value))
                        for index, (path, value) in enumerate(matches, start=1)
                    ],
                )
                selection = ask("Select a result to open (Enter to return): ").strip()
                if not selection:
                    continue
                selected_index = int(selection) - 1
                if selected_index < 0 or selected_index >= len(matches):
                    raise ValueError("Invalid result selection")
                dirty = (
                    edit_path_guided(
                        doc,
                        matches[selected_index][0],
                        decode_embedded=decode_embedded,
                    )
                    or dirty
                )
            except ValueError as exc:
                print("Error:", exc)
                continue
        elif choice == "5":
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            path = ask_with_path_completions(
                "New path (use '-' to append to arrays): ",
                doc.data,
                decode_embedded=decode_embedded,
                include_append=True,
            )
            try:
                value_type = choose(
                    "Type (auto/string/int/float/bool/null/json): ",
                    VALUE_TYPES[1:],
                )
                value = parse_typed_value(ask("Value: "), value_type)
                doc.data = add_path(doc.data, path, value, decode_embedded=decode_embedded)
                dirty = True
                print("Added.")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "6":
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            path = ask_with_path_completions(
                "Path to delete: ", doc.data, decode_embedded=decode_embedded
            )
            try:
                dirty = delete_path_guided(doc, path, decode_embedded=decode_embedded) or dirty
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "7":
            raw_depth = ask("Max depth (blank for 2): ").strip()
            try:
                max_depth = int(raw_depth) if raw_depth else 2
                if max_depth < 0:
                    raise ValueError
            except ValueError:
                print("Depth must be a non-negative number.")
                continue
            try:
                limit = ask_non_negative_int("Limit (blank for 100): ", 100)
            except ValueError as exc:
                print("Error:", exc)
                continue
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            paths = iter_paths(
                doc.data,
                max_depth=max_depth,
                decode_embedded=decode_embedded,
            )
            for count, (path, value) in enumerate(paths, start=1):
                if count > limit:
                    break
                try:
                    formatted_path = path.to_dot()
                except ValueError:
                    formatted_path = path.to_pointer()
                print(f"{formatted_path} ({type(value).__name__})")
        elif choice == "8":
            if not dirty:
                render_status("No changes to save.", kind="info")
                continue
            try:
                result = doc.save(backup=True)
            except (OSError, ValueError, ConcurrentModificationError) as exc:
                print("Error:", exc)
                continue
            dirty = False
            print(f"Saved. Backup: {result.backup_path}")
            if not result.durability_confirmed:
                print(
                    "Warning: the file was replaced successfully, "
                    "but directory durability could not be confirmed."
                )
            if not result.snapshot_confirmed:
                render_status(
                    "The file was written, but its current state could not be re-verified. "
                    "Reload the document before making additional changes.",
                    kind="error",
                )
                return
        elif choice == "9":
            if dirty:
                confirm = ask("Unsaved changes. Exit anyway? (yes/no): ")
                if not confirm.lower().startswith("y"):
                    continue
            print("Bye.")
            return
        else:
            print("Invalid option.")
