## Why

The README offers two install modes: the plugin, and `install.sh` / `install.ps1`, which copy (or symlink) the repo into `~/.claude/skills/cq-design/`. The README says the installer gives "no slash commands", while `commands/*.md` require `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_DATA}` and `SKILL.md` resolves `SKILL_DIR` from the "Base directory" line. Nothing states which entry points work in which mode, and copy-install behaviour had never been tested.

## What Changes

- Verified: a copy install is loaded as a `cq-design@skills-dir` plugin; the `/cq-design:*` commands are offered and `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_DATA}` are defined. The skill path also works from copy and `--link` installs.
- Correct the README ("With the installer (no slash commands)") and state in `README.md` and `SKILL.md` that both modes support skill and commands, and how the venv location differs.
- Make `SKILL.md` Prerequisites state both `SKILL_DIR` sources.

No script, schema, command-body, or installer changes.

## Capabilities

### New Capabilities

### Modified Capabilities
- `plugin-packaging`: "Installer path remains supported" gains the support statement and the venv-location difference.

## Impact

- `SKILL.md` and `README.md` only.
- Delta spec for `plugin-packaging`.
