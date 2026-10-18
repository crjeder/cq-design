---
name: cq-design
description: Design or redesign 3D-printable parts as parametric CadQuery models. Use when the user asks to design, model, fix printability of, or generate an STL for a 3D-printed part -- mentions like "3D print", "3D-printable", "STL", "CadQuery", "gridfinity", "print me a", "printable enclosure/bracket/mount/case/holder/box/lid/stand", "design a part to print", "redesign for printability".
---

# cq-design

Commands (`/cq-design:design`, `plan`, `init`, `update`, `build`, `render`, `status`) are plugin
files in `commands/`; each states its own steps. This file is the pipeline contract they share.

## Prerequisites

`SKILL_DIR` is the absolute path of this file's directory (`${CLAUDE_PLUGIN_ROOT}` in a
plugin install or an installer copy, which Claude Code loads as a plugin
too), taken from the "Base directory for this skill" line (`$BASH_SOURCE` / `$PSCommandPath` resolve to the working directory
in a one-off shell). Both install modes offer the commands; the venv is `${CLAUDE_PLUGIN_DATA}/venv`
when set up by `/cq-design:init`, `$SKILL_DIR/.venv` from the installer. Substitute the literal path into every command; shell variables do not
persist between calls. Every invocation is documented at the step that uses it -- never run
`--help`. Generated output goes to the working directory.

Once per working directory (all idempotent): run `/cq-design:init` logic (see `commands/init.md`).

`init_permissions.py` merges the permission patterns and hooks into
`.claude/settings.local.json`, creates `build/`, `stl/`, `preview/`, and seeds
`profile.json` / `skill_config.json` when absent (never overwrites). When it
reports seeding a file, tell the user where to edit it. If the profile fails validation,
report the errors and ask for those fields in Phase 1. If the helper cannot run, merge
`src/skill_permissions.json`'s `allow` array into `.claude/settings.local.json` by hand.
Run scripts as `uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/<script>.py"`.

**If `build/journal.md` already exists, read `skill/resume.md` in full before Phase 0.**

## Phases

Each phase's detail file is mandatory reading before the phase starts; the phase is not
runnable from this summary.

| Phase | Read first | Does |
|-------|-----------|------|
| 0 Sourcing triage | `skill/phase0_sourcing.md` | Search for a usable existing model; rungs 1-3 skip phases 1-3 |
| 1 Requirements | `skill/phase1_requirements.md` | Function, topology, dimensions (research agent), fits; one approval checkpoint |
| 2 Planning | `skill/phase2_planning.md` | Planner agent writes `BUILD_PLAN.json`; validate; user approves the summary |
| 3 Build | `skill/phase3_build.md` | Builder + auditor agents per part, design approval, print orientation, export, quality gate |
| 4 Deliver | `skill/phase4_deliver.md` | Report, `README.md`, `REGENERATE.md` |

Agents get everything they need from prompts rendered by `src/render_prompt.py`; do not
read reference documents, `inventory.json`, or preview images into this session for them.

## Coordinate system

North / East / South / West / Up / Down = +Y / +X / -Y / -X / +Z / -Z. Three right-handed
frames: the **build pose** (per part, chosen by the planner; the builder works in it), the
**assembly pose** (shared; `pose_intent` + builder-written `placement`, rotation and
translation only), and the **print pose** (chosen by the orientation optimizer, Z = 0 is
the bed). Every deliverable is in print pose.
