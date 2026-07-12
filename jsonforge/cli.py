import argparse
import json
import sys

from .core.casting import smart_cast
from .core.document import JsonDocument
from .core.paths import add_path, delete_path, format_value, get_path, iter_paths, set_path
from .core.search import search
from .tui.app import run_interactive


def cmd_validate(args) -> int:
    JsonDocument.load(args.file)
    print("valid")
    return 0


def cmd_get(args) -> int:
    doc = JsonDocument.load(args.file)
    match = get_path(doc.data, args.path)
    print(format_value(match.value))
    return 0


def cmd_set(args) -> int:
    doc = JsonDocument.load(args.file)
    set_path(doc.data, args.path, smart_cast(args.value))
    backup_path = doc.save(backup=not args.no_backup)
    if backup_path:
        print(f"backup: {backup_path}")
    print("updated")
    return 0


def cmd_add(args) -> int:
    doc = JsonDocument.load(args.file)
    add_path(doc.data, args.path, smart_cast(args.value))
    backup_path = doc.save(backup=not args.no_backup)
    if backup_path:
        print(f"backup: {backup_path}")
    print("added")
    return 0


def cmd_delete(args) -> int:
    doc = JsonDocument.load(args.file)
    delete_path(doc.data, args.path)
    backup_path = doc.save(backup=not args.no_backup)
    if backup_path:
        print(f"backup: {backup_path}")
    print("deleted")
    return 0


def cmd_search(args) -> int:
    doc = JsonDocument.load(args.file)
    found = False
    for path, value in search(doc.data, args.query):
        found = True
        preview = format_value(value).replace("\n", " ")
        if len(preview) > args.preview:
            preview = preview[: args.preview - 3] + "..."
        print(f"{path}: {preview}")
    return 0 if found else 1


def cmd_tree(args) -> int:
    doc = JsonDocument.load(args.file)
    for path, value in iter_paths(doc.data, max_depth=args.depth):
        print(f"{path}\t{type(value).__name__}")
    return 0


def cmd_interactive(args) -> int:
    run_interactive(args.file)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Universal terminal JSON editor")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="Validate a JSON file")
    validate.add_argument("file")
    validate.set_defaults(func=cmd_validate)

    get = subparsers.add_parser("get", help="Print value at a dot path")
    get.add_argument("file")
    get.add_argument("path")
    get.set_defaults(func=cmd_get)

    set_cmd = subparsers.add_parser("set", help="Set value at a dot path")
    set_cmd.add_argument("file")
    set_cmd.add_argument("path")
    set_cmd.add_argument("value")
    set_cmd.add_argument("--no-backup", action="store_true")
    set_cmd.set_defaults(func=cmd_set)

    add = subparsers.add_parser("add", help="Add object key or array item")
    add.add_argument("file")
    add.add_argument("path")
    add.add_argument("value")
    add.add_argument("--no-backup", action="store_true")
    add.set_defaults(func=cmd_add)

    delete = subparsers.add_parser("delete", help="Delete object key or array item")
    delete.add_argument("file")
    delete.add_argument("path")
    delete.add_argument("--no-backup", action="store_true")
    delete.set_defaults(func=cmd_delete)

    search_cmd = subparsers.add_parser("search", help="Search paths and values")
    search_cmd.add_argument("file")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--preview", type=int, default=120)
    search_cmd.set_defaults(func=cmd_search)

    tree = subparsers.add_parser("tree", help="List paths in a JSON document")
    tree.add_argument("file")
    tree.add_argument("--depth", type=int, default=2)
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
        except (OSError, json.JSONDecodeError) as exc:
            print(f"jsonforge: {exc}", file=sys.stderr)
            return 2

    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        try:
            return args.func(args)
        except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            print(f"jsonforge: {exc}", file=sys.stderr)
            return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
