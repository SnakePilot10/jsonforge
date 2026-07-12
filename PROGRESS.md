# JsonForge Progress

## Current Status

JsonForge has an initial MVP repository with a universal JSON core, CLI commands, and a simple `prompt_toolkit` interactive menu. Current CLI support includes `validate`, `get`, `set`, `add`, `delete`, `search`, `tree`, and `interactive`.

## Decisions

- The project is domain-neutral. No game-specific logic belongs in the core.
- Python is used for the MVP because iteration is fast and `prompt_toolkit` is already available in the Termux environment.
- Dot paths are the first supported addressing model because they are simple to type in a terminal.
- Strings containing JSON arrays or objects are decoded during traversal and re-encoded when edited, preserving the original string-backed storage shape.
- Saving creates timestamped backups by default for destructive write operations.
- Backup names include collision handling so multiple writes in the same second do not overwrite earlier backups.

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
- Added initial README.
- Added initial unit tests for casting, embedded JSON, paths, and search.

## In Progress

- MVP verified. Next work should focus on path escaping and better interactive tree navigation.

## Next Steps

- Add path escaping for object keys containing dots.
- Add tree browsing mode.
- Add better type previews and compact/pretty output modes.
- Decide whether to stay with prompt-style UI or introduce a full-screen TUI later.

## Known Issues

- Dot-path syntax cannot address object keys that contain dots.
- Original JSON formatting is not preserved; files are written with two-space indentation.
- Search may produce duplicate matches when a key and path both match the query.

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
