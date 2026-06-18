## Context

Claude Code discovers personal skills under `~/.claude/skills/<name>/`. The
cq-design skill is a directory containing `SKILL.md`, `src/`, `prompts/`,
`reference/`, and a uv-managed Python project (`pyproject.toml` + `uv.lock`).
Today installation is manual: place the repo in the skills directory and run
`uv sync` to create the `.venv`. `SKILL.md` already documents dual-platform use
(POSIX shell + PowerShell) and pins Python 3.12 via `.python-version`, with
`uv` as the environment manager.

The skill invokes its scripts as `uv run --project "$SKILL_DIR" python ...`, so
the installed copy must be a self-contained uv project with its environment
provisioned in place.

## Goals / Non-Goals

**Goals:**
- One command installs the skill so Claude Code can discover it.
- Provision the Python environment in the installed location via `uv sync`.
- Work on macOS, Linux (POSIX shell) and Windows (PowerShell).
- Idempotent: re-running updates an existing install without manual cleanup.
- Provide an uninstall path.

**Non-Goals:**
- Installing `uv` itself (the script detects it and points at the install URL).
- Project-scoped installs (`.claude/skills/` inside another repo) - personal
  install only for the first version.
- Publishing to a plugin marketplace or any registry.
- Modifying the skill's pipeline behavior or the JSON contract.

## Decisions

**Copy vs. symlink the skill into the skills directory.**
Default to **copy**. Claude Code reads the skill from `~/.claude/skills/cq-design/`;
a copy is robust across editors and OSes (Windows symlinks need elevation or
developer mode). Offer a `--link`/`-Link` flag for contributors who want edits in
the repo to reflect live. Copy excludes throwaway artifacts (`.git`, `.venv`,
`__pycache__`, caches, `build/`, `BUILD_PLAN.json`) so the destination is clean.
Alternative considered: symlink-by-default - rejected because of Windows
friction and because a stray repo move would silently break the install.

**Provision the environment in the destination, not the source.**
After staging files, run `uv sync` with the destination as the project dir so
`.venv` is created there. This matches the existing installed layout (a copy
with its own `.venv`) and keeps the source repo's `.venv` independent.
Alternative: point `SKILL_DIR` back at the source repo - rejected; defeats the
purpose of an install and couples Claude Code to the checkout location.

**Two thin entry points, shared logic per platform.**
`install.sh` (POSIX) and `install.ps1` (PowerShell). Each is self-contained
rather than shelling out to a common implementation, to avoid a bash dependency
on Windows. Both honor `CLAUDE_SKILLS_DIR` (or a `--dest` flag) to override the
default `~/.claude/skills` target, which also makes them testable.

**Preflight checks before mutating anything.**
Verify `uv` is on PATH first; if missing, print the install URL
(`https://docs.astral.sh/uv/`) and exit non-zero before touching the skills
directory.

## Risks / Trade-offs

- [Copy drifts from the repo over time] → `--link` flag for contributors;
  re-running the installer refreshes a copied install.
- [`uv sync` is slow or downloads Python on first run] → expected and
  documented; the script streams uv output so the user sees progress.
- [Overwriting an existing install loses local edits] → re-install replaces only
  skill files (never the user's other skills); document that copied installs are
  not an edit surface and point contributors at `--link`.
- [Windows symlink creation fails without privilege] → copy is the default;
  `-Link` surfaces a clear error if symlink creation is denied.

## Migration Plan

Additive. No existing install is broken: a user who manually placed the skill
can re-run the installer to normalize the layout. Uninstall removes only
`~/.claude/skills/cq-design/`.
