## Why

cq-design can be installed two ways: as a plugin (`/plugin install`) and as a standalone skill (`install.sh` / `install.ps1` into `~/.claude/skills/cq-design/`). With both present, Claude Code lists every skill, command and agent twice, the two copies can be at different commits, and nothing tells the user. `/cq-design:init` and `/cq-design:status` are the places a user looks when something is off, and neither checks for this.

## What Changes

- New read-only script `src/install_check.py` that reports whether the plugin copy and the standalone skill copy are both present, where each lives, and (when `.version.json` / git info is available) whether their commits differ. JSON contract plus a one-line text form.
- `/cq-design:status` runs it and reports a duplicate install with the removal hint (`install.sh --uninstall` or `/plugin uninstall`).
- `/cq-design:init` runs it and warns (never blocks, never removes anything).
- Detection only. Nothing is deleted or modified.

## Capabilities

### New Capabilities
- `duplicate-install-detection`: detect and report that the plugin and the standalone skill are both installed.

### Modified Capabilities
- `plugin-commands`: `status` also reports a duplicate install; `init` warns about one.

## Impact

- New `src/install_check.py` and `tests/test_install_check.py` (stdlib only, no CadQuery).
- `commands/status.md`, `commands/init.md`; `FILES.md`, `reference/scripts.md`.
- `TODO.md` line 25 and `documentation/todo-pipeline.md` entry removed when done.
