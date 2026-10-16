## Context

Two install modes exist. Plugin: marketplace install. Copy/link (`install.sh`, `install.ps1`): the repo lands in `~/.claude/skills/cq-design/` and `uv sync --project <dest>` creates the venv inside it.

Verified (task 1): Claude Code loads a copy install as a plugin with source `cq-design@skills-dir`, because the copy carries `.claude-plugin/plugin.json`. A headless `claude -p` run against a clean config dir with only the copy listed `cq-design:build/design/init/plan/render/status/update` as slash commands. In a live session, `/cq-design:status` expanded `${CLAUDE_PLUGIN_ROOT}` to the skills-dir path, and a plugin data dir `~/.claude/plugins/data/cq-design-skills-dir/` exists, so `${CLAUDE_PLUGIN_DATA}` is defined too. The README's "(no slash commands)" and the premise that commands need the marketplace install are both wrong.

Real difference: the venv location. A copy install has an installer venv at `<dest>/.venv`; the commands (`init`, `design`, `plan`) use `${CLAUDE_PLUGIN_DATA}/venv` via `UV_PROJECT_ENVIRONMENT`. Both work; the second is created on first `/cq-design:init`. `--link` points `${CLAUDE_PLUGIN_ROOT}` through the symlink at the repo checkout (not separately verified).

## Goals / Non-Goals

**Goals:**
- State accurately that both install modes support the skill and the `/cq-design:*` commands, and where the venv lives in each.
- Correct the README heading and any text implying copy installs lack commands.

**Non-Goals:**
- Changing installers, command bodies, or path resolution.
- Unifying the two venvs.

## Decisions

- **Document, do not change code.** Commands already resolve in copy installs. Alternative: add `.claude-plugin` exclusion to the installers so copies stay skill-only. Rejected: it removes working behaviour and the report asks to state support, not shrink it.
- **No per-command note.** Every command is supported in both modes, so a note on seven files adds nothing. Instead each `commands/*.md` is unchanged and `SKILL.md` carries one sentence on both `SKILL_DIR` sources and the venv difference.
- **`--link` verified only for the skill path**; command loading from a symlinked skills dir is left as stated-unverified in the README rather than claimed.

## Risks / Trade-offs

- [Two venvs on a copy install, one from the installer and one from `/cq-design:init`] -> documented; disk cost only.
- [`skills-dir` plugin loading is Claude Code behaviour, not ours] -> README cites the observed `cq-design@skills-dir` source so a reader can check it with `claude plugin list`.
- [Out of scope bug seen: `.version.json` in the user's copy install has a UTF-8 BOM, so `skill_version.py` reports it unreadable and `bundle_project.py --check` prints `unknown`] -> likely written by `install.ps1`; track as a separate change.
