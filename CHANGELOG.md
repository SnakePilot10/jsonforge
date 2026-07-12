# Changelog

## Unreleased

- Harden destructive writes with atomic temp-file replacement.
- Preserve numeric object keys as strings while still supporting numeric array indexes.
- Support escaped dots and backslashes in path segments.
- Make `add` fail on existing object keys unless `--force` is used.
- Add explicit CLI value typing with `--type`.
- Deduplicate search results.

## 0.1.0

- Initial MVP with validation, get, set, add, delete, search, tree, interactive mode, backups, and embedded JSON traversal.
