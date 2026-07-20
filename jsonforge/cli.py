import argparse
import json
import sys

from .core.casting import parse_typed_value
from .core.document import ConcurrentModificationError, JsonDocument, SaveResult
from .core.paths import add_path, delete_path, format_value, get_path, iter_paths, set_path, JsonPath
from .core.search import format_search_display, search
from .tui.app import run_interactive


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def preview_size(value: str) -> int:
    parsed = int(value)
    if parsed < 3:
        raise argparse.ArgumentTypeError("must be greater than or equal to 3")
    return parsed


def render_path(path: JsonPath, path_format: str) -> str:
    if path_format == "pointer":
        return path.to_pointer()
    try:
        return path.to_dot()
    except ValueError as exc:
        raise ValueError(
            "Path cannot be represented as a dot path; "
            "use --path-format pointer"
        ) from exc


def cmd_validate(args) -> int:
    JsonDocument.load(args.file, allow_duplicate_keys=args.allow_duplicate_keys)
    print("valid")
    return 0


def cmd_get(args) -> int:
    doc = JsonDocument.load(args.file)
    match = get_path(
        doc.data,
        args.path,
        decode_embedded=args.decode_embedded,
        path_format=args.path_format,
    )
    print(format_value(match.value))
    return 0


def cmd_set(args) -> int:
    doc = JsonDocument.load(args.file)
    doc.data = set_path(
        doc.data,
        args.path,
        parse_typed_value(args.value, args.type),
        decode_embedded=args.decode_embedded,
        path_format=args.path_format,
    )
    result = doc.save(backup=not args.no_backup, force_write=args.force_write)
    print_save_result(result)
    print("updated")
    return save_exit_code(result)


def cmd_add(args) -> int:
    doc = JsonDocument.load(args.file)
    doc.data = add_path(
        doc.data,
        args.path,
        parse_typed_value(args.value, args.type),
        force=args.force,
        decode_embedded=args.decode_embedded,
        path_format=args.path_format,
    )
    result = doc.save(backup=not args.no_backup, force_write=args.force_write)
    print_save_result(result)
    print("added")
    return save_exit_code(result)


def cmd_delete(args) -> int:
    doc = JsonDocument.load(args.file)
    doc.data = delete_path(
        doc.data,
        args.path,
        decode_embedded=args.decode_embedded,
        path_format=args.path_format,
    )
    result = doc.save(backup=not args.no_backup, force_write=args.force_write)
    print_save_result(result)
    print("deleted")
    return save_exit_code(result)


def print_save_result(result: SaveResult) -> None:
    if result.backup_path:
        print(f"backup: {result.backup_path}")
    if result.replaced and not result.durability_confirmed:
        print(
            "warning: the file was replaced successfully, "
            "but directory durability could not be confirmed",
            file=sys.stderr,
        )


def save_exit_code(result: SaveResult) -> int:
    if result.replaced and not result.durability_confirmed:
        return 3
    return 0


def cmd_search(args) -> int:
    doc = JsonDocument.load(args.file)
    found = False
    for path, value in search(
        doc.data,
        args.query,
        scope=args.scope,
        exact=args.exact,
        limit=args.limit,
        offset=args.offset,
        decode_embedded=args.decode_embedded,
        display_path_format=args.path_format,
    ):
        found = True
        formatted_path = render_path(path, args.path_format)

        preview = format_search_display(value).replace("\n", " ")
        if len(preview) > args.preview:
            preview = preview[: args.preview - 3] + "..."
        print(f"{formatted_path}: {preview}")
    return 0 if found else 1


def cmd_tree(args) -> int:
    doc = JsonDocument.load(args.file)
    paths = iter_paths(doc.data, max_depth=args.depth, decode_embedded=args.decode_embedded)
    for path, value in paths:
        formatted_path = render_path(path, args.path_format)
        print(f"{formatted_path}\t{type(value).__name__}")
    return 0


def cmd_interactive(args) -> int:
    run_interactive(args.file)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Universal terminal JSON editor")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="Validate a JSON file")
    validate.add_argument("file")
    validate.add_argument("--allow-duplicate-keys", action="store_true")
    validate.set_defaults(func=cmd_validate)

    get = subparsers.add_parser("get", help="Print the value at a JSON path")
    get.add_argument("file")
    get.add_argument("path")
    get.add_argument(
        "--path-format",
        choices=["dot", "pointer"],
        default="dot",
        help="Syntax used by PATH",
    )
    get.add_argument(
        "--decode-embedded",
        action="store_true",
        help="Treat string values containing JSON arrays or objects as traversable JSON",
    )
    get.set_defaults(func=cmd_get)

    set_cmd = subparsers.add_parser("set", help="Set value at a JSON path")
    set_cmd.add_argument("file")
    set_cmd.add_argument("path")
    set_cmd.add_argument("value")
    set_cmd.add_argument(
        "--type",
        choices=["auto", "string", "int", "float", "bool", "null", "json"],
        default="auto",
    )
    set_cmd.add_argument(
        "--path-format",
        choices=["dot", "pointer"],
        default="dot",
        help="Syntax used by PATH",
    )
    set_cmd.add_argument(
        "--decode-embedded",
        action="store_true",
        help="Allow edits inside string values containing JSON arrays or objects",
    )
    set_cmd.add_argument("--no-backup", action="store_true")
    set_cmd.add_argument(
        "--force-write",
        action="store_true",
        help="Overwrite even if the file changed since it was loaded",
    )
    set_cmd.set_defaults(func=cmd_set)

    add = subparsers.add_parser("add", help="Add object key or array item")
    add.add_argument("file")
    add.add_argument("path")
    add.add_argument("value")
    add.add_argument(
        "--type",
        choices=["auto", "string", "int", "float", "bool", "null", "json"],
        default="auto",
    )
    add.add_argument("--force", action="store_true", help="Replace an existing object key")
    add.add_argument(
        "--path-format",
        choices=["dot", "pointer"],
        default="dot",
        help="Syntax used by PATH",
    )
    add.add_argument(
        "--decode-embedded",
        action="store_true",
        help="Allow additions inside string values containing JSON arrays or objects",
    )
    add.add_argument("--no-backup", action="store_true")
    add.add_argument(
        "--force-write",
        action="store_true",
        help="Overwrite even if the file changed since it was loaded",
    )
    add.set_defaults(func=cmd_add)

    delete = subparsers.add_parser("delete", help="Delete object key or array item")
    delete.add_argument("file")
    delete.add_argument("path")
    delete.add_argument(
        "--path-format",
        choices=["dot", "pointer"],
        default="dot",
        help="Syntax used by PATH",
    )
    delete.add_argument(
        "--decode-embedded",
        action="store_true",
        help="Allow deletes inside string values containing JSON arrays or objects",
    )
    delete.add_argument("--no-backup", action="store_true")
    delete.add_argument(
        "--force-write",
        action="store_true",
        help="Overwrite even if the file changed since it was loaded",
    )
    delete.set_defaults(func=cmd_delete)

    search_cmd = subparsers.add_parser("search", help="Search JSON keys, paths, and values")
    search_cmd.add_argument("file")
    search_cmd.add_argument("query")
    search_cmd.add_argument(
        "--in",
        dest="scope",
        choices=["key", "path", "value", "display", "all"],
        default="all",
    )
    search_cmd.add_argument("--exact", action="store_true")
    search_cmd.add_argument("--limit", type=non_negative_int, default=50)
    search_cmd.add_argument("--offset", type=non_negative_int, default=0)
    search_cmd.add_argument(
        "--path-format",
        choices=["dot", "pointer"],
        default="dot",
        help="Syntax used for PATH in search results",
    )
    search_cmd.add_argument(
        "--decode-embedded",
        action="store_true",
        help="Search inside string values containing JSON arrays or objects",
    )
    search_cmd.add_argument("--preview", type=preview_size, default=120)
    search_cmd.set_defaults(func=cmd_search)

    tree = subparsers.add_parser("tree", help="List paths in a JSON document")
    tree.add_argument("file")
    tree.add_argument("--depth", type=non_negative_int, default=2)
    tree.add_argument(
        "--path-format",
        choices=["dot", "pointer"],
        default="dot",
        help="Syntax used for PATH in tree output",
    )
    tree.add_argument(
        "--decode-embedded",
        action="store_true",
        help="List paths inside string values containing JSON arrays or objects",
    )
    tree.set_defaults(func=cmd_tree)

    interactive = subparsers.add_parser("interactive", help="Open interactive prompt")
    interactive.add_argument("file")
    interactive.set_defaults(func=cmd_interactive)
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    commands = {"validate", "get", "set", "add", "delete", "search", "tree", "interactive"}
    if len(argv) == 1 and argv[0] not in commands and not argv[0].startswith("-"):
        try:
            run_interactive(argv[0])
            return 0
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"jsonforge: {exc}", file=sys.stderr)
            return 2

    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        try:
            return args.func(args)
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            ConcurrentModificationError,
        ) as exc:
            print(f"jsonforge: {exc}", file=sys.stderr)
            return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
