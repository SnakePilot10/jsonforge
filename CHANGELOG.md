# Changelog

## Unreleased

- Harden destructive writes with atomic temp-file replacement.
- Preserve numeric object keys as strings while still supporting numeric array indexes.
- Support escaped dots and backslashes in path segments.
- Make `add` fail on existing object keys unless `--force` is used.
- Add explicit CLI value typing with `--type`.
- Deduplicate search results.
- Reject non-standard `NaN` and `Infinity` values when loading, casting, or saving JSON.
- Fix mutations when the document root is a string containing embedded JSON.
- Validate list insertion indexes consistently.
- Make search match JSON scalar spelling such as `null`, `true`, and `false`.

## 0.1.0

- Initial MVP with validation, get, set, add, delete, search, tree, interactive mode, backups, and embedded JSON traversal.
