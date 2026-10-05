## Why

A project directory's `lib/`, `build/build.py`, and `.claude/settings.local.json` are
snapshots of the skill taken at export time. Nothing records which skill commit they came
from, re-bundling leaves deleted modules behind and clobbers a user-edited `pyproject.toml`,
and refreshing a project takes several manual commands that are documented nowhere.

## What Changes

- `bundle_project.py` writes `.bundle_version.json` (skill commit, dirty flag, timestamp) into the project.
- `bundle_project.py --check [DIR]` reports `current` / `behind` / `unknown` by comparing the stamp to the skill's commit (reuses `skill_version.py`); exit 0 only when current. Changes nothing.
- Re-running `bundle_project.py` prunes files in `lib/` that the bundle no longer ships.
- `pyproject.toml` and `.python-version` are written only when absent; if an existing one differs from the template, the run prints a note and keeps it.
- Re-running `bundle_project.py` also merges permissions/hooks (`init_permissions.merge_*`, already additive), so one command refreshes all three layers.
- `skill/resume.md` and README document the "update an existing project" flow: `skill_version.py --compare`, reinstall if stale, `bundle_project.py DIR`, `uv sync`.
- **BREAKING**: a re-bundle no longer overwrites an existing `pyproject.toml` / `.python-version`.

## Capabilities

### New Capabilities
- `project-bundle-update`: stamping, staleness check, pruning, and one-command refresh of a bundled project directory.

### Modified Capabilities
- `self-contained-build-environment`: pyproject/.python-version are scaffolded only when absent; bundle refresh also prunes stale tooling.

## Impact

- `src/bundle_project.py`, `src/skill_version.py` (reuse compare helper), `src/init_permissions.py` (call only)
- `skill/resume.md`, `README.md`, `reference/scripts.md`, `CLAUDE.md` (file layout line)
- `tests/test_build_script.py` (uses `bundle`), new `tests/test_bundle_project.py` (fast, no CadQuery)
