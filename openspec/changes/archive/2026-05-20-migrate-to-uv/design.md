## Context

The project currently ships a `requirements.txt` that users install manually into a venv they create themselves. This has two compounding problems: (1) there is no enforcement of the Python 3.10-3.12 constraint, so users on 3.13+ silently get broken OCC wheel installs; (2) `cq_warehouse` is fetched from git HEAD with no commit pinned, so installs on different days can diverge.

uv is the right tool here: it enforces `requires-python` before attempting any install, manages Python versions automatically via `.python-version`, and generates a lockfile that pins the `cq_warehouse` git commit SHA.

## Goals / Non-Goals

**Goals:**
- Single install command (`uv sync`) works on a clean clone
- Python 3.12 is used even if the user has only 3.13+ installed
- `cq_warehouse` git dep is locked to a specific commit in `uv.lock`
- Dev dependencies (pytest) are declared and installed by default
- All existing tests continue to pass unchanged

**Non-Goals:**
- Publishing the project to PyPI (this is a cloned workflow tool, not a library)
- Offline/bundled distribution (pip wheel cache, vendor directory)
- CI pipeline changes (out of scope for this change)
- Changing any runtime behavior of `src/` scripts

## Decisions

### D1: `pyproject.toml` with `[tool.uv] package = false`

The project is not a Python package - it has no importable top-level module intended for external use. Using `package = false` avoids requiring a build backend and prevents uv from attempting to build a wheel. This is the canonical uv pattern for workflow/tool projects.

Alternative considered: adding a `[build-system]` with `hatchling` or `setuptools`. Rejected - unnecessary complexity for a project that will never be published.

### D2: Commit `uv.lock`

The lockfile is committed so every clone gets byte-identical dependency versions. This is especially important for `cq_warehouse` (no PyPI releases, no tags - only HEAD). The locked commit SHA makes upstream changes opt-in rather than accidental.

Updating: `uv lock --upgrade-package cq-warehouse` followed by a deliberate commit.

Alternative considered: not committing the lockfile, relying on version ranges alone. Rejected - `cq_warehouse` has no version ranges to constrain it; without a lock it floats silently.

### D3: `.python-version` file containing `3.12`

uv reads `.python-version` and uses (or downloads) that exact CPython version for the venv. This is a zero-config solution for the Python version problem - no user action required.

Alternative considered: only `requires-python = ">=3.10,<3.13"` in pyproject.toml. This rejects wrong versions but does not auto-select the right one. Combined with `.python-version`, uv does the right thing automatically.

### D4: pytest in `[dependency-groups] dev`

pytest is a dev dependency that is already used but not declared. `uv sync` installs dev groups by default; `uv sync --no-dev` skips them for hypothetical production use. This is the uv-native grouping mechanism (PEP 735).

### D5: README is uv-only, no pip fallback

The project requires a specific Python version range regardless. Users who resist uv would need to manage Python version selection manually anyway. A single clear path is better than two paths with caveats.

## Risks / Trade-offs

- **cq_warehouse locked to a stale commit** → Mitigation: document `uv lock --upgrade-package cq-warehouse` in CLAUDE.md for deliberate updates.
- **Users without uv must install it first** → Mitigation: README links directly to `https://docs.astral.sh/uv/` with one-liner install command; uv install is a 10-second operation.
- **uv.lock is a large generated file** → Trade-off accepted; it is the source of truth for reproducibility.

## Migration Plan

1. Create `pyproject.toml` with all deps from `requirements.txt`
2. Create `.python-version` with `3.12`
3. Run `uv lock` to generate `uv.lock`
4. Verify: `uv sync` on a clean state, then `uv run pytest tests/` passes
5. Delete `requirements.txt`
6. Update `README.md` and `CLAUDE.md` setup sections
7. Commit all changes together

Rollback: `requirements.txt` is in git history; reverting the commit restores the old setup.
