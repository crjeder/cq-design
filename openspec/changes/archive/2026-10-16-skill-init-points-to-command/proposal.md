## Why

The init command lines (`uv sync`, `init_permissions.py`, `printer_profile_validate.py`) exist twice: in `SKILL.md` Prerequisites and in `commands/init.md`. The copies have already drifted (the command passes `--venv` and uses `${CLAUDE_PLUGIN_DATA}/venv`; SKILL.md does not). One copy removes the drift.

## What Changes

- `SKILL.md` Prerequisites: replace the inline command block with "run `/cq-design:init` logic (see `commands/init.md`)".
- Keep the surrounding SKILL.md prose that is not a command line (resume check, "run scripts as `uv run --project ...`").
- `commands/init.md` stays the single copy of the init command lines.

## Capabilities

### New Capabilities

### Modified Capabilities
- `plugin-commands`: `SKILL.md` must not duplicate the init command lines; it references `commands/init.md`.

## Impact

- `SKILL.md` (Prerequisites section only).
- `openspec/specs/plugin-commands/spec.md` (one added requirement).
- No script, schema, or test changes.
