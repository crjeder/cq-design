---
name: cq-design
description: Design or redesign 3D-printable parts as parametric CadQuery models. Use when the user asks to design, model, fix printability of, or generate an STL/3D-printed part -- mentions like "3D print", "STL", "CadQuery", "enclosure", "bracket", "mount", "case", "holder", "box", "lid", "stand", "gridfinity", "print me a", "design a part", "make a part for", "redesign for printability".
---

# cq-design

## Trigger

Activate when the user asks to design, model, or generate a 3D-printable part. Trigger phrases: "3D print", "STL", "CadQuery", "enclosure", "bracket", "mount", "case", "holder", "box", "lid", "stand", "gridfinity", "print me a", "design a part", "make a part for".

Also activate on these explicit slash commands:

| Command | Action |
|---------|--------|
| `/cq-design` | Full pipeline (phases 0-4) |
| `/plan` | Planning only (phases 1-2, stop after BUILD_PLAN.json is approved) |
| `/deliver <script.py>` | Export STL and 3MF for an existing script |
| `/render <script.py>` | Render a multi-view preview PNG for an existing script |

Read the first token to pick the command, then jump to its section below. For
`/cq-design` (or a natural-language trigger), start at Phase 0.

## Overview

A sourcing triage (Phase 0) ahead of a four-phase build pipeline: **Sourcing triage**
(usable existing model?) -> **Requirements** (Phase 1) -> **Planning** (Phase 2,
`BUILD_PLAN.json`) -> **Build** (Phase 3: part scripts, print orientation, model
export, quality gate) -> **Deliver** (Phase 4). Each phase section below carries a
summary and a mandatory pointer to its `skill/phase*.md` detail file — not optional
background.

## Prerequisites

Python 3.10-3.12 required (CadQuery has no wheels for 3.13+). Before running any skill
commands, establish `SKILL_DIR` — the absolute path to the directory containing this
file — since every `src/` script is invoked via `$SKILL_DIR/src/...`. Take it from the
"Base directory for this skill" line shown when the skill loaded; `$BASH_SOURCE` /
`$PSCommandPath` are empty in a one-off shell command and resolve to the working
directory instead. Substitute the literal path into each command (shell variables do not
persist between calls).

Every script's invocation is documented at the step that uses it — never run `--help`
to discover parameters. Generated output writes to the working directory, not
`$SKILL_DIR`.

**Before Phase 1 in a directory not yet seeded, read `skill/setup.md` in full** (venv,
permission bootstrap, printer-profile bootstrap). Skip to Phase 1 if already seeded
(`.claude/settings.local.json` has the patterns, `printer_profile.json` exists).

**If `build/journal.md` already exists, read `skill/resume.md` in full before Phase 0**
— it may be an interrupted run; resuming beats re-asking the user or restarting cold.

## Phase 0: Sourcing triage

Before designing from scratch, search for a usable existing model (parametric source,
BREP/STEP, or mesh) and classify the best find against a five-rung decision ladder;
requests resolved at rungs 1-3 skip Phase 1-3 entirely. Skipped on an explicit
from-scratch request; a quick single-pass search when the request is dominated by
user-specific dimensions.

**Before starting Phase 0, read `skill/phase0_sourcing.md` in full** — the decision
ladder, per-rung handling (reuse/convert, dumb-solid import, vet-then-deliver, partial
rebuild), and the mandatory license check.

## Phase 1: Requirements gathering

Collect the part's function, dimensions (or a product to look up), printer/material/DFM
constraints, and fit type; resolve topology ambiguity before generating a plan.
Real-world dimensions must be verified via the research agent's web lookup, never guessed.

**Before starting Phase 1, read `skill/phase1_requirements.md` in full** — topology
clarification, the research-agent dimension lookup, and the exit checkpoint
the user must approve before any plan is generated.

## Phase 2: Planning

Produce `BUILD_PLAN.json` from the planning prompt template, validate against schema,
write `parameters.py`, reconcile `printer_profile.json`, and present a plan summary for
user approval.

**Before starting Phase 2, read `skill/phase2_planning.md` in full** — prompt
placeholders, write/validate steps, `parameters.py` provenance, and the exact summary
format to approve.

## Phase 3: Build

One builder agent per part authors and validates its script (staged with user
checkpoints, or in one run), a fresh auditor agent judges the renders, then the user
approves the parts, print orientation is optimized, the model is exported, and the gate runs.

**Before starting Phase 3, read `skill/phase3_build.md` in full** — agent routing, stage
checkpoints, escalation, the audit, write-backs, design approval, print orientation,
model export, and the quality gate. This phase is not runnable from the summary alone.

## Phase 4: Deliver

Report status, previews, the print recipe, and output file locations, write
`README.md`, and export `REGENERATE.md` (the fresh-session regeneration prompt) with
`src/regen_prompt.py`.

**Before starting Phase 4, read `skill/phase4_deliver.md` in full** — exact report
contents, the `README.md` template, and the `REGENERATE.md` export.

## /plan command

Run phases 1-2 only, stop after approval, do not start the build. Useful when the user
wants to review and tweak the plan first.

## /deliver and /render commands

Both operate on an existing script (must assign geometry to `result`) via
`run_cadquery_model.py`:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" <script.py> --deliver --formats stl,3mf
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" <script.py> --preview
```

`/deliver` reports `result["stl"]`, `result["threemf"]`, a geometry summary (bbox,
volume, weight), and any `result["errors"]` — stop and show them if `success` is false.
`/render` displays the preview at `result["preview"]` and reports any errors.

## DFM constraints

Enforce in planning and during code review:

| Constraint | Value |
|------------|-------|
| Wall thickness | 1.2 mm min (3 perimeters @ 0.4 mm); 2.0 mm for load-bearing |
| Overhang limit | 45 deg max without supports |
| Bridge span | 20 mm reliable; ~50 mm with good cooling |
| Boolean overlap | Inner bodies extend 0.01+ mm past outer boundary |

**Clearance by fit type:** press_fit 0.0 mm, snap_fit 0.15 mm, sliding 0.25 mm,
loose/cover 0.5 mm. **Material adjustment** (from `printer_profile.json`): PLA +0.0 mm;
PETG +0.1 mm (stringing); TPU +0.2 mm (3.0 mm+ walls, prefer flexible snaps); ABS
+0.0 mm (mind warping) — also adjusts `wall_min_mm`.

## Coordinate system

North / East / South / West / Up / Down = +Y / +X / -Y / -X / +Z / -Z. Three
right-handed frames: the **part frame** (per part, chosen by the planner; dimensions and
interfaces live in it, the author builds in it), the **assembled frame** (shared;
`pose_intent` + author-written `placement`, rotation and translation only), and the
**print frame** (chosen by the orientation optimizer, Z = 0 is the bed). Every
deliverable is in print frame.

## Generated script rules

Every CadQuery script the pipeline produces must: begin with a flat
`from blocks import <function>` per block in `blocks_needed` (never import submodules);
define all dimensions in a `PARAMETERS` block at the top (no magic numbers); assign the
final geometry to a top-level `result`; never call `cq.exporters.export()`; build a
print-in-place revolute knuckle hinge via `blocks.joints.pin_hinge` rather than
hand-rolling one; assert construction-time invariants via `cq_verify`
(`verify_boolean`, `check_workplane`, `verify_feature_bounds`, `verify_backed`,
`verify_seated`, `verify_stage`); and reconcile a hand-edited `PARAMETERS` block back
into `BUILD_PLAN.json` via `src/import_params.py` rather than hand-editing the plan.
The full `cq_verify` reference and the scratch-part construction-plan contract live in
`prompts/part.md`.

## Error handling reference

Typed errors fall into four categories: OCC/geometry failures, `cq_verify.py`
construction-time assertion failures, DFM limit failures (`thin_wall`,
`overhang_exceeded`), and `visual_mismatch` (recorded by Claude in the part loop, not
emitted by the wrapper). Each error's exact name and `hint` are generated by
`run_cadquery_model.py`/`cq_verify.py` — see `reference/scripts.md` for the full list;
read the `hint`, don't guess a fix from the type name. All typed errors share the
3-attempt retry budget; after retries are exhausted, ask the user how to proceed
(different approach, a hint, or skip the part).

## Quick reference: key files

| File | Role |
|------|------|
| `BUILD_PLAN.json` / `src/build_plan_schema.json` | Generated plan / its JSON Schema |
| `printer_profile.json` | Printer/material/nozzle/constraint defaults |
| `src/run_cadquery_model.py` / `quality_gate.py` | Geometry validator / DFM gate |
| `src/plan_validate.py` | Validates BUILD_PLAN.json vs. schema + inventory |
| `prompts/research.md` / `planning.md` | Research and planner agent prompts |
| `prompts/builder.md` + `part.md` / `audit.md` | Builder and auditor agent prompts, rendered by `src/render_prompt.py` |
| `src/model_export.py` | Assembles unions into model.3mf + per-union/plate STL |
| `src/blocks/inventory.json` / `validate.py --search <kw>` | Block descriptors; lookup |
| `templates/archetypes.json` / `templates/*.py` | Known-good whole-part templates a builder starts from |
| `build/journal.md` | Append-only milestone log for resuming an interrupted run (see `skill/resume.md`) |
| `skill/*.md` | Setup and per-phase detail (see phase sections above) |
| `skill/resume.md` | Journal contract and interrupted-run resume procedure |
| `reference/hardware_dims.md` | Fastener sizing tables; read before authoring any part with a fastener block, never guess |
| `reference/gridfinity.md` | Gridfinity standard (grid/profiles/clearances); read before planning any Gridfinity request, never hand-model |
| `src/gridfinity_check.py` | Gridfinity conformance check (auto-run by the gate for Gridfinity parts) |
| `reference/CadQuery Pattern Reference.md` / `Anti-Patterns.md` | Idioms + mistakes, every part |
| `reference/emboss_text.md` / `servo_splines.md` | Read only when needed |
| `reference/FDM 3D Print Design Guidelines.md` | Guidelines for planning + parts |
