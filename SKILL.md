---
name: cq-design
description: Design or redesign 3D-printable parts as parametric CadQuery models. Use when the user asks to design, model, fix printability of, or generate an STL/3D-printed part -- mentions like "3D print", "STL", "CadQuery", "enclosure", "bracket", "mount", "case", "holder", "box", "lid", "stand", "gridfinity", "print me a", "design a part", "make a part for", "redesign for printability".
---

# cq-design

| Command | Action |
|---------|--------|
| `/cq-design` | Full pipeline (phases 0-4) |
| `/cq-plan` | Phases 1-2 only; stop once `BUILD_PLAN.json` is approved |
| `/deliver <script.py>` | Export STL and 3MF for an existing script |
| `/render <script.py>` | Render a multi-view preview PNG for an existing script |
| `/cq-design:update` | Re-copy the installed skill's tooling into this project's `lib/` and `build/build.py` |

## Prerequisites

`SKILL_DIR` is the absolute path of this file's directory, taken from the "Base directory
for this skill" line (`$BASH_SOURCE` / `$PSCommandPath` resolve to the working directory
in a one-off shell). Substitute the literal path into every command; shell variables do not
persist between calls. Every invocation is documented at the step that uses it -- never run
`--help`. Generated output goes to the working directory.

Once per working directory (all idempotent):

```bash
uv sync --project "$SKILL_DIR"
python "$SKILL_DIR/src/init_permissions.py" .
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/printer_profile_validate.py" profile.json
```

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

## /deliver and /render

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" <script.py> --deliver --formats stl,3mf
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" <script.py> --preview
```

The script must assign its geometry to `result`. `/deliver` reports `stl`, `threemf`, the
geometry summary, and any `errors` (stop and show them if `success` is false). `/render`
shows `preview` and any errors. Each error carries a `hint`; read it rather than guessing
from the type name.

## /cq-design:update

Only in a directory that already has `lib/` or `.bundle_version.json`; otherwise stop and
say the project was never bundled (run the normal pipeline). Then:

```bash
python "$SKILL_DIR/src/bundle_project.py" .
```

This always copies (no staleness check): `build_template.py` to `build/build.py`, the
bundled modules and `blocks`/`exporters` to `lib/`, prunes retired files, merges
permissions, and restamps `.bundle_version.json`. Report the new stamp commit and suggest
`uv sync` and `uv run python build/build.py`; do not run them or edit part scripts.

## Coordinate system

North / East / South / West / Up / Down = +Y / +X / -Y / -X / +Z / -Z. Three right-handed
frames: the **part frame** (per part, chosen by the planner; the builder works in it), the
**assembled frame** (shared; `pose_intent` + builder-written `placement`, rotation and
translation only), and the **print frame** (chosen by the orientation optimizer, Z = 0 is
the bed). Every deliverable is in print frame.
