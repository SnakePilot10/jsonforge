# JsonForge

JsonForge is a universal terminal JSON editor focused on safe edits, deep paths, and JSON embedded inside strings.

The project starts with a small `prompt_toolkit` interface and a CLI that can validate, read, set, and search any JSON file.

## Why It Exists

Real JSON files often contain nested data in awkward forms, including JSON serialized as a string:

```json
{
  "settings": "{\"theme\":\"dark\",\"enabled\":true}"
}
```

JsonForge treats that string as editable structure when traversing paths, then writes it back as a string so the original shape is preserved.

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
```

Set a path with automatic backup:

```bash
python -m jsonforge set file.json settings.enabled true
```

Add a key or append to an array:

```bash
python -m jsonforge add file.json settings.new_key '{"nested":true}'
python -m jsonforge add file.json items.- new_item
```

Delete a key or array index:

```bash
python -m jsonforge delete file.json settings.old_key
python -m jsonforge delete file.json items.0
```

List paths:

```bash
python -m jsonforge tree file.json --depth 3
```

Search paths and values:

```bash
python -m jsonforge search file.json enabled
```

## Path Syntax

Paths are dot-separated:

```text
object.key
array.0.name
settings.embedded.key
```

Array indexes are numeric path segments. Object keys that contain literal dots are not supported yet.

## Current Scope

- Universal JSON load/save.
- Backup before write.
- Smart value casting.
- Dot-path `get` and `set`.
- Dot-path `add` and `delete`.
- Path listing with `tree`.
- Search across keys, paths, values, and embedded JSON strings.
- Basic interactive menu using `prompt_toolkit`.

## Non-Goals For The MVP

- Domain-specific save editors.
- Schema-specific forms.
- Full-screen visual tree rendering.
- Preserving original whitespace or key formatting.
