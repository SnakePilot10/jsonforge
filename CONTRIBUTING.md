# Contributing

JsonForge is early-stage. Keep changes small, tested, and documented in `PROGRESS.md`.

## Development Setup

```bash
python -m pip install -e '.[dev]'
```

## Checks

```bash
python -m compileall jsonforge tests
python -m pytest
python -m jsonforge --help
```

## Design Rules

- Keep the core domain-neutral.
- Do not add file-format-specific behavior to `jsonforge/core`.
- Destructive operations must either be atomic, backed up, or explicitly documented as unsafe.
- Add tests for path engine changes, especially embedded JSON cases.
- Update `PROGRESS.md` with decisions, completed work, known issues, and verification notes.
