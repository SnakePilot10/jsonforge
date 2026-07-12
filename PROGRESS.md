# JsonForge Progress

## Current Status

JsonForge has an initial hardened MVP with a universal JSON core, CLI commands, and a simple `prompt_toolkit` interactive menu. Current CLI support includes `validate`, `get`, `set`, `add`, `delete`, `search`, `tree`, and `interactive`.

## Decisions

- The project is domain-neutral. No game-specific logic belongs in the core.
- Python is used for the MVP because iteration is fast and `prompt_toolkit` is already available in the Termux environment.
- Dot paths are the first supported addressing model because they are simple to type in a terminal.
- Dot path conversion now depends on the current container: arrays use numeric indexes and objects keep string keys, including numeric-looking keys.
- Dots and backslashes in object keys are escaped with backslashes in paths.
- Strings containing JSON arrays or objects are decoded during traversal and re-encoded when edited, preserving the original string-backed storage shape.
- Saving creates timestamped backups by default for destructive write operations.
- Backup names include collision handling so multiple writes in the same second do not overwrite earlier backups.
- Saves are atomic: data is written to a temporary file, flushed, fsynced, validated, and then swapped into place with `os.replace()`.

## Completed

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
- Added package metadata, MIT license, changelog, contributing notes, and GitHub Actions tests.
- Added initial README.
- Added initial unit tests for casting, embedded JSON, paths, and search.

## In Progress

- Safe writes and path engine v2 are implemented. Next work should focus on richer interactive tree navigation and compact/pretty output controls.

## Next Steps

- Add tree browsing mode.
- Add better type previews and compact/pretty output modes.
- Decide whether to stay with prompt-style UI or introduce a full-screen TUI later.

## Known Issues

- Original JSON formatting is not preserved; files are written with two-space indentation.
- Root-level scalar strings containing embedded JSON are not yet replaceable through the mutating path helpers because helpers currently mutate containers in place.

## Test Notes

### 2026-07-12

- `python -m compileall jsonforge tests` passed.
- `python -m unittest discover -s tests` passed: 10 tests.
- `python -m pytest` passed: 16 tests after installing pytest globally.
- `python -m jsonforge --help` passed.
- `python -m jsonforge validate tests/fixtures/sample.json` passed.
- `python -m jsonforge get tests/fixtures/sample.json settings.theme` returned `"dark"` through embedded JSON traversal.
- `python -m jsonforge search tests/fixtures/sample.json dark` found `settings.theme`.
- `python -m jsonforge set /data/data/com.termux/files/home/.cache/opencode/tmp/jsonforge_sample.json settings.enabled true` passed on a temp copy and created a backup.
- `python -m jsonforge add ... settings.extra 123`, `get`, `delete`, and `tree --depth 2` passed on a temp copy.
- Consecutive `set` commands in the same second created unique backups using `_1` suffix collision handling.
- `python -m compileall jsonforge tests` passed after safe-writes/path-v2 hardening.
- `python -m pytest` passed: 26 tests.
- `python -m pip install -e .` passed after adding `build-system` and project metadata.
- CLI smoke tests passed for escaped dot paths, `--type string`, `add` duplicate rejection, and `python -m jsonforge search` returning exit code 1 on no matches.
