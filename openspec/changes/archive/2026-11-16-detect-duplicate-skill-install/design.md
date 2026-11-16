## Context

Two install routes exist: the plugin (Claude Code records it in `~/.claude/plugins/installed_plugins.json`, key `cq-design@<marketplace>`, entries carry `installPath`, `version`, `gitCommitSha`) and the standalone skill (`install.sh` / `install.ps1` copy or symlink into `$CLAUDE_SKILLS_DIR` or `~/.claude/skills/cq-design/`, a copy carrying `.version.json`). `skill_version.py` already describes one install; it does not look for the other.

## Goals / Non-Goals

**Goals:** report both-installed with both locations and, where known, both commits; wire it into `status` and `init`; stdlib only, fast.

**Non-Goals:** removing either copy, choosing a winner, detecting project-level `.claude/skills/` copies, other plugin marketplaces' renamed forks.

## Decisions

- **New `src/install_check.py`, not an extension of `skill_version.py`.** `skill_version` describes the copy it runs from; this answers a different question (what else is installed). Imports `describe` helpers from nothing: it reads `.version.json` directly, three lines. Alternative (flag on `skill_version.py`) rejected to keep that script's contract unchanged.
- **Plugin detection via `installed_plugins.json`**, keys whose name part before `@` is `cq-design`. Config dir from `CLAUDE_CONFIG_DIR` else `~/.claude`. Absent or unparseable file means "plugin: not found", never an error.
- **Standalone detection** = `<skills dir>/cq-design/SKILL.md` exists, skills dir from `CLAUDE_SKILLS_DIR` else `<config dir>/skills`. A symlink counts and reports its target.
- **Both present is the only warning state.** Output JSON: `plugin` and `standalone` (each `null` or `{path, commit}`), `duplicate` bool, `commits_differ` bool or null when either commit is unknown, `hint` string. Exit 0 always; the commands decide wording.
- **Paths overridable by flags** (`--config-dir`, `--skills-dir`) so tests use `tmp_path` without touching the real home.

## Risks / Trade-offs

- `installed_plugins.json` format is Claude Code's, not ours, and may change → tolerate any shape, treat unknown as not found; the test pins the shape seen today.
- A plugin entry can outlive a deleted cache dir → also require `installPath` to exist before counting it.
- A standalone copy installed to a custom `--dest` is invisible → documented limitation; `CLAUDE_SKILLS_DIR` covers the supported override.
