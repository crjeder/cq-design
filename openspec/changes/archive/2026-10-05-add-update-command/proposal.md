## Why

A project's `build/build.py` and `lib/` are snapshots of the skill taken when it was last
bundled. Refreshing them is a four-command recipe documented in `README.md` and
`skill/resume.md`; there is no single command, so users run it by hand or forget.

## What Changes

- Add a `/cq-design:update` command row to `SKILL.md` and a short section: it re-copies the installed skill tooling (`src/` -> project `lib/`, `build/build.py`) via `bundle_project.py`, unconditionally.
- Refer the two existing "Updating an existing project" doc sections to the command.
- No script changes: `bundle_project.py` already does the refresh. `install.sh` and
  `install.ps1` are not touched (updating the installed skill itself stays a manual reinstall).

## Capabilities

### New Capabilities
- `update-command`: the `/cq-design:update` command that refreshes a project's bundled tooling to the installed skill version.

### Modified Capabilities

## Impact

- `SKILL.md`, `README.md`, `skill/resume.md` (docs only).
- No code, schema, or dependency changes.
