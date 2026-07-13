from jsonforge.core.casting import smart_cast
from jsonforge.core.document import JsonDocument
from jsonforge.core.paths import (
    add_path,
    delete_path,
    format_value,
    get_path,
    iter_paths,
    path_completions,
    set_path,
)
from jsonforge.core.search import search

from .prompts import ask, ask_with_completions, choose


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
            try:
                match = get_path(doc.data, path)
                print(format_value(match.value))
                if match.decoded_embedded_segments:
                    print(f"Decoded embedded JSON segments: {match.decoded_embedded_segments}")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "3":
            path = ask_with_completions("Path: ", path_completions(doc.data))
            try:
                current = get_path(doc.data, path).value
                print("Current:", format_value(current))
                value = smart_cast(ask("New value: "))
                doc.data = set_path(doc.data, path, value)
                dirty = True
                print("Updated.")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "4":
            query = ask("Search: ")
            count = 0
            try:
                for path, value in search(doc.data, query, limit=50):
                    count += 1
                    preview = format_value(value).replace("\n", " ")
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
            try:
                value = smart_cast(ask("Value: "))
                doc.data = add_path(doc.data, path, value)
                dirty = True
                print("Added.")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "6":
            path = ask_with_completions("Path to delete: ", path_completions(doc.data))
            confirm = ask(f"Delete '{path}'? (yes/no): ")
            if not confirm.lower().startswith("y"):
                print("Delete cancelled.")
                continue
            try:
                doc.data = delete_path(doc.data, path)
                dirty = True
                print("Deleted.")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                print("Error:", exc)
        elif choice == "7":
            raw_depth = ask("Max depth (blank for 2): ").strip()
            try:
                max_depth = int(raw_depth) if raw_depth else 2
            except ValueError:
                print("Depth must be a number.")
                continue
            for path, value in iter_paths(doc.data, max_depth=max_depth):
                type_name = type(value).__name__
                print(f"{path} ({type_name})")
        elif choice == "8":
            backup_path = doc.save(backup=True)
            dirty = False
            print(f"Saved. Backup: {backup_path}")
        elif choice == "9":
            if dirty:
                confirm = ask("Unsaved changes. Exit anyway? (yes/no): ")
                if not confirm.lower().startswith("y"):
                    continue
            print("Bye.")
            return
        else:
            print("Invalid option.")
