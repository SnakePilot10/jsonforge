# Changelog

## Unreleased

- Unify display search rendering with `format_search_line()` so `scope="display"` matches exactly the printed line including `--preview` truncation.
- Validate `display_path_format` at runtime; raise `ValueError` for unknown formats.
- Move `render_path()` to `core/paths.py`; CLI now raises a descriptive error instead of falling back silently to pointer when `--path-format dot` cannot represent the path.
- Expand `JsonPath` usage and JSON Pointer support to `search` and `tree` commands.
- Add `--path-format` flag to `search` and `tree` in the CLI.
- Match search queries in `scope="path"` and `scope="display"` against both dot-path and JSON Pointer formats.
- Refactor `iter_paths` and `search` core functions to use `JsonPath` objects internally.
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
- Reject negative and non-numeric delete indexes for arrays.
- Preserve basic file metadata during atomic saves.
- Refuse saves through symlink paths to avoid replacing links.
- Match search queries against raw object keys as well as escaped paths.
- Handle strict JSON errors cleanly in shorthand interactive invocation.
- Keep embedded JSON strings as strings unless `--decode-embedded` is requested.
- Make path traversal lazy and iterative.
- Add search scopes, exact matching, limits, offsets, and display-line matching.
- Reject duplicate object keys during strict JSON load by default.
- Add the large stress JSON fixture and bounded traversal/search tests.
- Align the interactive menu with explicit search scopes, limits, offsets, embedded decoding, and typed edits.
- Preserve object, array, and null types strictly when using interactive preserve mode.
- Preserve string-backed embedded JSON storage when replacing an embedded node directly.
- Validate interactive choices and reject unsupported search scopes.
- Keep display search compact for containers instead of serializing full subtrees.
- Align display search with rendered search output for strings and escaped scalar values.
- Introduce `JsonPath` and JSON Pointer parsing/formatting, with pointer support for `get`.
- Reject ambiguous `JsonPath` dot conversion for the root empty key and require strict ASCII array indexes.
- Add JSON Pointer path-format support to `set`, `add`, and `delete`.

## 0.1.0

- Initial MVP with validation, get, set, add, delete, search, tree, interactive mode, backups, and embedded JSON traversal.
