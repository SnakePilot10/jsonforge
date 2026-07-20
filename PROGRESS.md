# JsonForge Progress

## Current Status

JsonForge has an initial hardened MVP with a universal JSON core, CLI commands, and a simple `prompt_toolkit` interactive menu. Current CLI support includes `validate`, `get`, `set`, `add`, `delete`, `search`, `tree`, and `interactive`.

## Decisions

- The project is domain-neutral. No game-specific logic belongs in the core.
- Python is used for the MVP because iteration is fast and `prompt_toolkit` is already available in the Termux environment.
- Dot paths are the first supported addressing model because they are simple to type in a terminal.
- Dot path conversion now depends on the current container: arrays use numeric indexes and objects keep string keys, including numeric-looking keys.
- Dots and backslashes in object keys are escaped with backslashes in paths.
- Strings containing JSON arrays or objects stay strings by default. Traversal or mutation inside them is opt-in through `--decode-embedded` or the equivalent interactive prompt.
- Saving creates timestamped backups by default for destructive write operations.
- Backup names include collision handling so multiple writes in the same second do not overwrite earlier backups.
- Backups are reserved with exclusive creation, flushed, fsynced, and never created through a pre-existing path entry.
- Saves are atomic: data is written to a temporary file, flushed, fsynced, validated, and then swapped into place with `os.replace()`.
- Atomic saves preserve file permissions, do not preserve old mtimes, and reject symlink paths instead of replacing the link.
- Loaded documents keep a file snapshot; saves reject external modification unless `force_write` / `--force-write` is used explicitly.
- JSON handling is strict: `NaN`, `Infinity`, and `-Infinity` are rejected during load, cast, and save.
- Duplicate object keys are rejected during load and validation unless compatibility is requested explicitly.
- Path traversal and search use iterative stacks so callers can consume bounded result sets incrementally.
- `JsonPath` is the initial structured path representation. JSON Pointer parsing/formatting is implemented for canonical addressing and is wired into `get`, `set`, `add`, `delete`, `search`, and `tree`.
- Array indexes now require strict ASCII JSON Pointer-style spelling: `0` or digits without leading zeroes.
- Interactive dot-path completion resolves only the current parent and suggests its immediate object keys or array indexes instead of traversing the full document.

## Completed

### 2026-07-20

- Refactorizado `iter_paths` y `search` para aceptar y retornar objetos `JsonPath` internamente.
- Actualizado la TUI interactiva para utilizar `JsonPath.to_dot()` con fallback seguro a pointer, y `path_completions` para filtrar rutas no representables en dot-path.
- Agregado soporte en la CLI para `--path-format` (`dot` o `pointer`) en los comandos `search` y `tree`.
- Implementado matching de rutas en `search` con semántica diferenciada: `scope="path"` compara contra dot-path y JSON Pointer simultáneamente; `scope="display"` evalúa únicamente contra la representación seleccionada por `--path-format`.
- Centralizado el renderizado de salida con `format_search_line()` compartida entre la lógica de matching y la CLI, asegurando que `--preview` recorte afecte también al matching de `scope="display"`.
- Movido `render_path()` a `core/paths.py` para evitar duplicación entre CLI y search.
- Agregada validación en tiempo de ejecución para `display_path_format` (levanta `ValueError` si el valor no es `dot` ni `pointer`).
- La CLI ahora falla con error descriptivo en lugar de cambiar silenciosamente a Pointer cuando `--path-format dot` no puede representar la ruta.
- Actualizada toda la suite de pruebas para validar con `JsonPath` en lugar de strings de rutas.
- Agregadas pruebas de regresión para: clave vacía en la raíz, display con preview recortado, validación de display_path_format, y escapes JSON Pointer `~0`/`~1`.
- Corregido estilo de líneas largas en `document.py` y `test_document.py` para cumplir con el límite de 100 caracteres.
- Endurecido `render_path()` para aceptar únicamente los formatos `dot` y `pointer` y rechazar valores desconocidos.
- Agregada validación de `preview >= 3` en `search()` y `format_search_line()` antes de recorrer o renderizar resultados.
- Corregida la descripción de `scope="path"` y `scope="display"` en el changelog.
- Integrados `ruff check .` y `ruff format --check .` en GitHub Actions para proteger lint y formato.
- Reemplazado el autocompletado plano de rutas por un `PathCompleter` dinámico que sugiere únicamente los hijos del nodo actual.
- Agregado autocompletado contextual a los flujos interactivos de get, set, add y delete, incluyendo `-` para append en arrays.
- Integrado el autocompletado con el recorrido opcional de JSON embebido y con claves dot-path escapadas.

### 2026-07-12

- Created repository at `~/Projects/Python/jsonforge/`.
- Initialized git repository.
- Added Python package layout.
- Added `pyproject.toml` with `prompt_toolkit` dependency and `jsonforge` script entry point.
- Implemented `smart_cast` for terminal input conversion.
- Implemented embedded JSON detection and re-encoding helpers.
- Implemented dot-path read and write operations.
- Implemented JSON document load/save/backup wrapper.
- Implemented recursive search across normal and embedded JSON values.
- Implemented CLI commands: `validate`, `get`, `set`, `search`, and `interactive`.
- Added CLI commands: `add`, `delete`, and `tree`.
- Implemented a minimal prompt-based interactive menu.
- Added path autocompletion for interactive `get`, `set`, and `delete` flows.
- Fixed backup name collisions for multiple writes within the same second.
- Added atomic writes for save operations.
- Fixed numeric object keys so they are not mistaken for array indexes.
- Added escaped path support for dots and backslashes in object keys.
- Made `add` fail on existing object keys unless `--force` is used.
- Added explicit CLI value type parsing via `--type`.
- Deduplicated search output.
- Fixed root embedded JSON mutation by making mutating path helpers return the updated root.
- Rejected non-standard JSON constants during validation, parsing, casting, and saving.
- Tightened array insertion semantics so out-of-range and negative indexes fail instead of silently appending or inserting from the end.
- Made search match JSON scalar spellings like `null`, `true`, and `false`.
- Tightened array deletion semantics so negative and non-numeric indexes fail.
- Made search compare raw object keys in addition to escaped paths.
- Added clean error handling for strict JSON failures in shorthand interactive invocation.
- Added package metadata, MIT license, changelog, contributing notes, and GitHub Actions tests.
- Added initial README.
- Added initial unit tests for casting, embedded JSON, paths, and search.
- Made embedded JSON traversal opt-in and added `--decode-embedded` to relevant CLI commands.
- Converted path listing to lazy iterative traversal.
- Added bounded search with `key`, `path`, `value`, `display`, and `all` scopes, exact matching, limits, and offsets.
- Fixed `limit=0` so it returns zero search results.
- Added duplicate-key rejection to strict JSON loading with explicit compatibility opt-out.
- Added the large stress JSON fixture under `tests/fixtures/json_stress_test.json`.
- Added stress fixture tests for strict load, partial traversal, and bounded search.
- Improved the interactive menu with explicit typed edits, search scope/exact/limit/offset prompts, embedded decode prompts, bounded tree output, and save error handling.
- Fixed interactive preserve mode so objects remain objects, arrays remain arrays, and null requires `null` input.
- Fixed direct replacement of string-backed embedded JSON nodes so storage remains a string when `decode_embedded` is enabled.
- Added validation for interactive choices and unsupported search scopes.
- Made display search use compact placeholders for containers instead of serializing full subtrees.
- Aligned display search with rendered search output for strings and escaped scalar values.
- Started Path Engine v3 by adding `JsonPath`, JSON Pointer parsing/formatting, and `get --path-format pointer`.
- Hardened `JsonPath.to_dot()` so the single empty key is not rendered as the document root, and tightened array index parsing.
- Added JSON Pointer support to `set`, `add`, and `delete` by routing mutations through `JsonPath` coercion.
- Hardened save operations with stable-load snapshots, external modification detection, exclusive backup creation, structured `SaveResult`, post-replace durability reporting, and `--force-write` for snapshot conflicts only.

## In Progress

- Core semantics and bounded traversal/search are being stabilized for `0.2.0`. Next work should focus on converting deep mutations to iterative operations and polishing recovery workflows.

## Next Steps

- Convert deep mutations (`set`, `add`, `delete`) from recursive helpers to iterative operations.
- Add CLI and documentation polish around recovery workflows for unconfirmed directory durability.
- Add operation preview/dry-run support before destructive saves.
- Add richer stress and property tests for paths, mutations, round-trips, and unusual keys.

## Known Issues

- Original JSON formatting is not preserved; files are written with two-space indentation.
- Root replacement for scalar non-container documents is still intentionally unsupported by path helpers.
- Dot-path display still cannot represent every possible key safely; the single empty key is rejected during `JsonPath.to_dot()` conversion.
- Deep mutations are still recursive and can hit Python recursion limits on extremely deep documents.
- Safe writes cannot cryptographically prove a file is unchanged if another process restores all tracked snapshot fields before save.

## Test Notes

### 2026-07-20

- `python -m pytest` pasó: 115 tests tras implementar JsonPath y `--path-format` en search y tree.
- `python -m pytest` pasó: 120 tests tras alinear semántica de display y formato dot-path.
- `python -m pytest` pasó: 122 tests tras unificar format_search_line, validar display_path_format, y corregir líneas largas.
- `ruff check .` pasó tras endurecer las validaciones de rutas y preview.
- `ruff format --check .` pasó: 20 archivos correctamente formateados.
- `python -m compileall jsonforge tests` pasó tras integrar Ruff en CI.
- `python -m pytest` pasó: 125 tests tras agregar las validaciones de formatos desconocidos y previews demasiado pequeños.
- `ruff check .` y `ruff format --check .` pasaron tras implementar el autocompletado contextual.
- `python -m compileall jsonforge tests` pasó tras integrar `PathCompleter`.
- `python -m pytest` pasó: 132 tests tras cubrir hijos contextuales, filtros parciales, arrays, append, JSON embebido y claves escapadas.

### 2026-07-12

- `python -m compileall jsonforge tests` passed.
- `python -m unittest discover -s tests` passed: 10 tests.
- `python -m pytest` passed: 16 tests after installing pytest globally.
- `python -m jsonforge --help` passed.
- `python -m jsonforge validate tests/fixtures/sample.json` passed.
- `python -m jsonforge get tests/fixtures/sample.json settings.theme --decode-embedded` returned `"dark"` through opt-in embedded JSON traversal.
- `python -m jsonforge search tests/fixtures/sample.json dark --decode-embedded` found `settings.theme`.
- `python -m jsonforge set /data/data/com.termux/files/home/.cache/opencode/tmp/jsonforge_sample.json settings.enabled true` passed on a temp copy and created a backup.
- `python -m jsonforge add ... settings.extra 123`, `get`, `delete`, and `tree --depth 2` passed on a temp copy.
- Consecutive `set` commands in the same second created unique backups using `_1` suffix collision handling.
- `python -m compileall jsonforge tests` passed after safe-writes/path-v2 hardening.
- `python -m pytest` passed: 26 tests.
- `python -m pip install -e .` passed after adding `build-system` and project metadata.
- CLI smoke tests passed for escaped dot paths, `--type string`, `add` duplicate rejection, and `python -m jsonforge search` returning exit code 1 on no matches.
- `python -m pytest` passed: 37 tests after strict JSON and root embedded JSON regression coverage.
- CLI smoke tests passed for root embedded JSON mutation and `validate` rejecting `Infinity` with exit code 2.
- `python -m pytest` passed: 44 tests after delete-index, metadata, symlink, raw-key search, and shorthand strict-error regressions.
- `ruff check .` passed after core semantics/search updates.
- `python -m pytest` passed: 54 tests after opt-in embedded JSON traversal, lazy path iteration, scoped search, and duplicate-key rejection.
- `python -m pytest` passed: 57 tests after adding the large stress fixture.
- `ruff check .` passed after search-boundary and interactive parity fixes.
- `python -m pytest` passed: 65 tests after `limit=0`, display search, CLI validation, type preservation, and stress search coverage.
- `python -m pytest` passed: 73 tests after strict preserve-mode, embedded-node replacement, scope validation, and compact display-search regressions.
- `python -m pytest` passed: 78 tests after display-output alignment and additional embedded string-storage regressions.
- `python -m pytest` passed: 87 tests after introducing `JsonPath`, JSON Pointer parsing/formatting, and pointer `get` coverage.
- `ruff check .` passed after hardening `JsonPath.to_dot()` and array index parsing.
- `python -m compileall jsonforge` passed after hardening `JsonPath.to_dot()` and array index parsing.
- `python -m pytest` passed: 95 tests after adding ambiguous dot conversion and strict array index regressions.
- `ruff check .` passed after adding JSON Pointer mutations.
- `python -m compileall jsonforge` passed after adding JSON Pointer mutations.
- `python -m pytest` passed: 103 tests after adding JSON Pointer mutation coverage.
- `python -m pytest` passed: 112 tests after safe-write snapshot, exclusive backup, and durability-result hardening.
- `python -m compileall jsonforge tests` passed after safe-write hardening.
- `ruff check .` was not run locally because this Termux environment attempted to build Ruff from source and the build was cancelled to avoid excessive CPU usage.
