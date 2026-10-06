## Why

cq-design installs today via `install.sh` / `install.ps1`, which copy the repo into `~/.claude/skills/` and run `uv sync`. Users must clone, run a platform script, and re-run it to update. A Claude Code plugin gives one-line install and update (`/plugin install`), namespaced slash commands, and a stable per-plugin data directory.

## What Changes

- Add `.claude-plugin/plugin.json` (name `cq-design`) with the repo root as the plugin root; the existing root `SKILL.md` stays the single skill (`"skills": ["."]`), so no files move.
- Add `.claude-plugin/marketplace.json` so the repo itself is an installable marketplace.
- Add `commands/` with seven `/cq-design:<name>` commands: `design`, `plan`, `init`, `update`, `deliver`, `render`, `status`.
- Promote the ad-hoc command table in `SKILL.md` (`/cq-design`, `/cq-plan`, `/deliver`, `/render`, `/cq-design:update`) to real command files; `SKILL.md` keeps the phase contract and drops the table.
- Resolve `SKILL_DIR` from `${CLAUDE_PLUGIN_ROOT}` and keep the Python venv in `${CLAUDE_PLUGIN_DATA}` so it survives plugin updates.
- Keep `install.sh` / `install.ps1` as the alternative (non-plugin) path.

Not added as commands: `resume` (automatic when `build/journal.md` exists), `eval` (developer-only), `profile` (covered by `init` and `status`).

## Capabilities

### New Capabilities
- `plugin-packaging`: plugin manifest, marketplace entry, plugin-root path resolution, persistent venv location.
- `plugin-commands`: the seven namespaced commands and what each runs.

### Modified Capabilities
<!-- none: update-command behavior is unchanged, it just becomes a plugin command file -->

## Impact

- New: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `commands/*.md`.
- Edited: `src/init_permissions.py` (`--venv`, stale-hook replacement), `SKILL.md` (command table, Prerequisites path resolution), `README.md` (install section), `CLAUDE.md` (file layout).
- Installers: no change needed; they copy `commands/` harmlessly.
- The plugin cache is replaced on update, so nothing mutable may live under the plugin root (the `.venv` is the one current offender).
