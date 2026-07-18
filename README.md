# JsonForge

JsonForge is a universal terminal JSON editor focused on safe edits and deep paths.

The project starts with a small `prompt_toolkit` interface and a CLI that can validate, read, set, add, delete, search, and list paths in any JSON file.

## Why It Exists

Real JSON files often contain nested data in awkward forms, including JSON serialized as a string:

```json
{
  "settings": "{\"theme\":\"dark\",\"enabled\":true}"
}
```

JsonForge keeps that value as a string by default. If you explicitly pass `--decode-embedded`, commands can treat string values containing JSON arrays or objects as traversable structure and then write them back as strings.

JsonForge also rejects non-standard JSON constants such as `NaN`, `Infinity`, and `-Infinity` during load, cast, and save operations.

Atomic saves preserve file permissions, refuse to replace symlink paths, and do not preserve the old modification time. If you need to edit a symlinked file, pass the target path explicitly.

JsonForge records a snapshot when a document is loaded and refuses to save if the file changed before write. Use `--force-write` only when you intentionally want to overwrite a file that changed since loading; it does not bypass JSON validation, symlink checks, permissions, or safe temporary-file creation.

## Install For Development

```bash
python -m pip install -e .
```

## Usage

Open interactive mode:

```bash
python -m jsonforge file.json
python -m jsonforge interactive file.json
```

Validate JSON:

```bash
python -m jsonforge validate file.json
```

Read a path:

```bash
python -m jsonforge get file.json users.0.name
python -m jsonforge get file.json settings.theme --decode-embedded
python -m jsonforge get file.json /users/0/name --path-format pointer
```

Set a path with automatic backup:

```bash
python -m jsonforge set file.json settings.enabled true
python -m jsonforge set file.json device.id 00123 --type string
python -m jsonforge set file.json settings.theme light --decode-embedded
python -m jsonforge set file.json /users/0/name Ada --path-format pointer --type string
python -m jsonforge set file.json settings.enabled true --force-write
```

Add a key or append to an array:

```bash
python -m jsonforge add file.json settings.new_key '{"nested":true}'
python -m jsonforge add file.json settings.new_key replacement --force
python -m jsonforge add file.json items.- new_item
python -m jsonforge add file.json settings.new_key true --decode-embedded
python -m jsonforge add file.json /users/- '{"name":"New"}' --path-format pointer --type json
```

Delete a key or array index:

```bash
python -m jsonforge delete file.json settings.old_key
python -m jsonforge delete file.json items.0
python -m jsonforge delete file.json settings.old_key --decode-embedded
python -m jsonforge delete file.json /obsolete --path-format pointer
```

List paths:

```bash
python -m jsonforge tree file.json --depth 3
python -m jsonforge tree file.json --depth 3 --decode-embedded
```

Search keys, paths, and values:

```bash
python -m jsonforge search file.json enabled
python -m jsonforge search file.json enabled --in key --exact
python -m jsonforge search file.json enabled --in value --limit 50 --offset 100
python -m jsonforge search file.json 'flags.tower_best_floor: 101' --in display
python -m jsonforge search file.json enabled --decode-embedded
```

The default search scope is `all`, which checks keys and scalar values. Use `--in path` or `--in display` when you specifically want to match full paths or the printed `path: value` line.

## Path Syntax

Dot paths are the default interactive syntax:

```text
object.key
array.0.name
settings.embedded.key
literal\.dot.key
literal\\backslash.key
```

Array indexes are numeric path segments only when the current container is an array. Numeric object keys stay strings, so `0` can address either object key `"0"` or array index `0` depending on the current value. Array indexes must be `0` or ASCII digits without leading zeroes.

Use backslash escaping for object keys containing dots or backslashes:

```bash
python -m jsonforge get file.json 'a\.b'
python -m jsonforge get file.json 'a\\b'
```

JSON Pointer is available as the canonical path format for `get`, `set`, `add`, and `delete`:

```bash
python -m jsonforge get file.json '/users/0/name' --path-format pointer
python -m jsonforge get file.json '/a~1b' --path-format pointer
python -m jsonforge get file.json '/a~0b' --path-format pointer
python -m jsonforge get file.json '/' --path-format pointer
```

JSON Pointer escapes `~` as `~0` and `/` as `~1`. The pointer `/` addresses an empty object key at the document root; the empty pointer addresses the whole document.

## Value Types

By default, `set` and `add` use automatic casting:

```text
true -> boolean true
false -> boolean false
null -> JSON null
42 -> integer
3.14 -> float
{"a":1} -> object
hello -> string
```

If a value must stay a string, pass `--type string`:

```bash
python -m jsonforge set file.json device.id 00123 --type string
```

Supported explicit types are `auto`, `string`, `int`, `float`, `bool`, `null`, and `json`.

## Embedded JSON Strings

Strings are strings unless a command explicitly receives `--decode-embedded`. This prevents a value such as `"{\"a\":1}"` from silently changing from string semantics to object semantics during navigation.

`--decode-embedded` is available for `get`, `set`, `add`, `delete`, `search`, and `tree`.

## Current Scope

- Universal JSON load/save.
- Backup before write.
- Exclusive backup creation before write.
- Atomic save using temp-file replacement.
- File permission preservation during atomic save.
- External modification detection before save, with explicit `--force-write` override for that conflict only.
- Symlink save rejection to avoid replacing links by accident.
- Strict JSON constants: `NaN` and `Infinity` are rejected.
- Duplicate object keys are rejected by default during load and validation.
- Smart value casting.
- Explicit value typing with `--type`.
- Dot-path `get` and `set`.
- Initial `JsonPath` representation and JSON Pointer support for `get`, `set`, `add`, and `delete`.
- Dot-path `add` and `delete`.
- Escaped dots and backslashes in path segments.
- Opt-in mutation of JSON embedded in strings, including when the document root itself is an embedded JSON string.
- Path listing with `tree`.
- Search across keys and values by default, with explicit path/display scopes, exact matching, limit, and offset options.
- Search matching against both escaped paths and raw object key names.
- Basic interactive menu using `prompt_toolkit`.

## Non-Goals For The MVP

- Domain-specific save editors.
- Schema-specific forms.
- Full-screen visual tree rendering.
- Preserving original whitespace or key formatting.
