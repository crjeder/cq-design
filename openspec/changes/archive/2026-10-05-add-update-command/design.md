## Context

`bundle_project.py` already copies `build_template.py` -> `build/build.py` and the bundled
modules/packages -> `lib/`, prunes retired files, merges permissions, and stamps the commit
(spec `project-bundle-update`). The missing piece is a single entry point. `/deliver` and
`/render` are already command rows in `SKILL.md` that Claude interprets, not files the
installer registers.

## Goals / Non-Goals

**Goals:** one documented command that re-runs the initial-bundling copy from the installed skill.
**Non-Goals:** reinstalling the skill (`install.sh`/`install.ps1` stay untouched); merging
`pyproject.toml` changes; editing part scripts; running the build.

## Decisions

- **Command row in `SKILL.md`, no new script.** Matches `/deliver`; the installer already
  copies `SKILL.md`. The command is just `bundle_project.py .`.
- **No `--check` gate.** The commit stamp cannot see uncommitted edits or a linked skill
  checkout, so gating could skip a needed copy. The copy is idempotent.
- **Only gate: must already be a bundled project** (`lib/` or `.bundle_version.json`
  exists), so update never turns an arbitrary directory into a project.
- **Do not run `uv sync` / `build.py`.** Report them as next steps; a failing build after a
  `blocks` signature change is the user's call to fix.

## Risks / Trade-offs

- `/cq-design:update` is a documented convention, not a registered slash command, like the
  other rows. Real registration needs plugin packaging, out of scope here.
