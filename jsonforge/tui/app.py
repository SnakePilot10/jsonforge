from jsonforge.core.casting import parse_preserving_type, parse_typed_value
from jsonforge.core.document import ConcurrentModificationError, JsonDocument
from jsonforge.core.paths import (
    add_path,
    delete_path,
    format_value,
    get_path,
    iter_paths,
    path_completions,
    set_path,
)
from jsonforge.core.search import format_search_display, search

from .prompts import ask, ask_with_completions, choose

VALUE_TYPES = ["preserve", "auto", "string", "int", "float", "bool", "null", "json"]
SEARCH_SCOPES = ["key", "value", "path", "display", "all"]


def ask_non_negative_int(label: str, default: int) -> int:
    raw_value = ask(label).strip()
    if not raw_value:
        return default
    value = int(raw_value)
    if value < 0:
        raise ValueError("Value must be greater than or equal to 0")
    return value


def ask_yes_no(label: str) -> bool:
    return ask(label).strip().lower().startswith("y")


def run_interactive(json_file: str) -> None:
    doc = JsonDocument.load(json_file)
    dirty = False
    print(f"JsonForge: {doc.path}")

    while True:
        print("\n--- Main Menu ---")
        print("1) Show root keys")
        print("2) Get value by path")
        print("3) Set value by path")
        print("4) Search")
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
            path = ask_with_completions("Path: ", path_completions(doc.data))
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            try:
                match = get_path(doc.data, path, decode_embedded=decode_embedded)
                print(format_value(match.value))
                if match.decoded_embedded_segments:
                    print(f"Decoded embedded JSON segments: {match.decoded_embedded_segments}")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "3":
            path = ask_with_completions("Path: ", path_completions(doc.data))
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            try:
                current = get_path(doc.data, path, decode_embedded=decode_embedded).value
                print("Current:", format_value(current))
                value_type = choose(
                    "Type (preserve/auto/string/int/float/bool/null/json): ",
                    VALUE_TYPES,
                )
                raw_value = ask("New value: ")
                if value_type == "preserve":
                    value = parse_preserving_type(raw_value, current)
                else:
                    value = parse_typed_value(raw_value, value_type)
                doc.data = set_path(doc.data, path, value, decode_embedded=decode_embedded)
                dirty = True
                print("Updated.")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "4":
            query = ask("Search: ")
            count = 0
            try:
                scope = choose("Scope (key/value/path/display/all): ", SEARCH_SCOPES)
                exact = ask_yes_no("Exact match? (yes/no): ")
                limit = ask_non_negative_int("Limit (blank for 50): ", 50)
                offset = ask_non_negative_int("Offset (blank for 0): ", 0)
                decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
                matches = search(
                    doc.data,
                    query,
                    scope=scope,
                    exact=exact,
                    limit=limit,
                    offset=offset,
                    decode_embedded=decode_embedded,
                )
                for path, value in matches:
                    count += 1
                    preview = format_search_display(value).replace("\n", " ")
                    if len(preview) > 120:
                        preview = preview[:117] + "..."
                    print(f"{path}: {preview}")
            except ValueError as exc:
                print("Error:", exc)
                continue
            if count == 0:
                print("No matches.")
        elif choice == "5":
            path = ask("New path (use '-' to append to arrays): ")
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
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
            path = ask_with_completions("Path to delete: ", path_completions(doc.data))
            decode_embedded = ask_yes_no("Decode embedded JSON strings? (yes/no): ")
            confirm = ask(f"Delete '{path}'? (yes/no): ")
            if not confirm.lower().startswith("y"):
                print("Delete cancelled.")
                continue
            try:
                doc.data = delete_path(doc.data, path, decode_embedded=decode_embedded)
                dirty = True
                print("Deleted.")
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
            paths = iter_paths(doc.data, max_depth=max_depth)
            for count, (path, value) in enumerate(paths, start=1):
                if count > limit:
                    break
                print(f"{path} ({type(value).__name__})")
        elif choice == "8":
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
        elif choice == "9":
            if dirty:
                confirm = ask("Unsaved changes. Exit anyway? (yes/no): ")
                if not confirm.lower().startswith("y"):
                    continue
            print("Bye.")
            return
        else:
            print("Invalid option.")
