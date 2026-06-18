## Why

The current `requirements.txt` + manual venv setup creates friction for new users (wrong Python version, unpinned `cq_warehouse` git dep, multi-step install) and makes the repo fragile across time. Migrating to `uv` with a lockfile eliminates version drift and reduces setup to one command.

## What Changes

- Replace `requirements.txt` with `pyproject.toml` declaring all runtime and dev dependencies
- Add `.python-version` pinning Python 3.12 (uv downloads it automatically if missing)
- Generate and commit `uv.lock` to pin exact versions including the `cq_warehouse` git commit SHA
- Delete `requirements.txt`
- Update `README.md` setup instructions to `uv sync` only (no fallback)
- Update `CLAUDE.md` setup block to match

## Capabilities

### New Capabilities

- `uv-environment`: Project environment is defined by `pyproject.toml` + `uv.lock`. `uv sync` is the single install command; Python 3.12 is auto-managed. Dev dependencies (pytest) are declared in a `[dependency-groups]` dev group.

### Modified Capabilities

(none - no runtime behavior changes)

## Impact

- `requirements.txt` removed; `pyproject.toml` + `uv.lock` + `.python-version` added
- Existing `.venv/` (gitignored) is replaced by `uv`-managed venv on next `uv sync`
- `uv run pytest tests/` replaces direct `pytest` invocation in CLAUDE.md
- No changes to `src/`, `tests/`, prompts, or skill runtime behavior
