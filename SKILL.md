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

Read the first token of the user's message to pick the command, then jump to its
section below. For `/cq-design` (or a natural-language trigger), start at Phase 0.

## Overview

A sourcing triage (Phase 0) ahead of a four-phase build pipeline for parametric
3D-printable CadQuery models: **Sourcing triage** (Phase 0, checks for a usable
existing model before designing) -> **Requirements gathering** (Phase 1) ->
**Planning** (Phase 2, produces `BUILD_PLAN.json`) -> **Build** (Phase 3, part
scripts + print orientation + model export + quality gate) -> **Deliver** (Phase 4).
Each phase section below carries a summary and a mandatory pointer to its
`skill/phase*.md` detail file — not optional background.

## Prerequisites

Python 3.10-3.12 required (CadQuery has no wheels for 3.13+). Before running any skill
commands, establish `SKILL_DIR` — the absolute path to the directory containing this
file — since every `src/` script is invoked via `$SKILL_DIR/src/...`:

```bash
# macOS / Linux
SKILL_DIR="$(cd "$(dirname "$BASH_SOURCE")" && pwd)"
# Windows (PowerShell)
$SKILL_DIR = Split-Path -Parent (Resolve-Path $PSCommandPath)
```

Every script's invocation is documented in this file or a `skill/*.md` file at the step
that uses it — never run `--help` to discover parameters. Generated output always
writes to the working directory, not `$SKILL_DIR`.

**Before Phase 1 in a directory not yet seeded, read `skill/setup.md` in full** (venv,
permission bootstrap, printer-profile bootstrap). Skip straight to Phase 1 if already
seeded (`.claude/settings.local.json` has the patterns, `printer_profile.json` exists).

**If `build/journal.md` already exists in the working directory, read `skill/resume.md`
in full before Phase 0** — it may be an interrupted run; resuming without re-asking the
user or re-running finished phases is cheaper than restarting cold.

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
Real-world dimensions must be verified via web/Playwright lookup, never guessed.

**Before starting Phase 1, read `skill/phase1_requirements.md` in full** — topology
clarification, the Playwright lookup procedure, and the dimension validation checkpoint
the user must approve before any plan is generated.

## Phase 2: Planning

Produce `BUILD_PLAN.json` from the planning prompt template, validate against schema,
write `parameters.py`, reconcile `printer_profile.json`, and present a plan summary for
user approval.

**Before starting Phase 2, read `skill/phase2_planning.md` in full** — prompt
placeholders, write/validate steps, `parameters.py` provenance, and the exact summary
format to approve.

## Phase 3: Build

Write and validate each part script (autonomous or progressive), get user approval on
the finished parts, optimize print orientation, export the model, and run the gate.

**Before starting Phase 3, read `skill/phase3_build.md` in full** — the part loop
(archetype match, lint, visual self-review), progressive build staging, the design
approval checkpoint, print-orientation optimization, model export, the block library,
kinematic validation, and the quality gate. This phase is not runnable from the summary
alone.

## Phase 4: Deliver

Report status, previews, the print recipe, and output file locations, and write
`README.md`.

**Before starting Phase 4, read `skill/phase4_deliver.md` in full** — exact report
contents and the `README.md` template.

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
| Print bed face | Z = 0; `centered=(True, True, False)` on `.box()` |
| Boolean overlap | Inner bodies extend 0.01+ mm past outer boundary |

**Clearance by fit type:** press_fit 0.0 mm, snap_fit 0.15 mm, sliding 0.25 mm,
loose/cover 0.5 mm. **Material adjustment** (from `printer_profile.json`): PLA +0.0 mm;
PETG +0.1 mm (stringing); TPU +0.2 mm (3.0 mm+ walls, prefer flexible snaps); ABS
+0.0 mm (mind warping) — also adjusts `wall_min_mm`.

## Coordinate system

| Direction | Axis | Notes |
|-----------|------|-------|
| North / East / South / West | +Y / +X / -Y / -X | |
| Up / Down | +Z / -Z | Down is the print bed face, always Z = 0 |

## Request log

`BUILD_PLAN.json` may carry an optional `request_log`: an append-only, verbatim record
of the initial request plus every clarification/correction, each entry `{ts, kind,
text, images?}` (`kind` one of `initial`/`clarification`/`correction`; `images` an
optional array of repo-relative paths to sketches copied into `sketches/`). The planning prompt
(Phase 2) writes the `initial` entry and any Phase 1/2 clarifications. **Any later
clarification or correction the user gives mid-build (Phase 3 onward) must be appended
to `request_log` as a new dated entry — never edit, reorder, or remove existing
entries.** A correction that triggers re-planning carries the existing log forward
unchanged before the planning prompt appends the new entry.

## Generated script rules

Every CadQuery script the pipeline produces must: begin with a flat
`from blocks import <function>` per block in `blocks_needed` (never import submodules);
define all dimensions in a `PARAMETERS` block at the top (no magic numbers); assign the
final geometry to a top-level `result`; and never call `cq.exporters.export()` (the
wrapper handles export).

**Reconciling hand-edited PARAMETERS.** If a user (or Claude) tweaks a part script's
`PARAMETERS` block directly after the plan was built, `BUILD_PLAN.json` goes stale --
run `python src/import_params.py <script.py> --part <id> --write` to fold the edited
`width`/`depth`/`height` values back into that part's `dimensions` (schema-validated
before it writes). Do not hand-edit `BUILD_PLAN.json`'s dimensions to match; let the
tool do the round-trip so the plan stays the source of truth the quality gate checks
against.

**Construction-time verification (`cq_verify`).** A no-op `.cut()`/`.union()` and a
workplane-origin shift after `.center()`/`.hole()` both fail silently. Import from
`cq_verify` (on the wrapper's `PYTHONPATH`) and assert at the point of risk — each call
returns its post-op argument so it chains: `verify_boolean(body, body.cut(slot), "cut",
"vent_slot")`, or `check_workplane(wp, label, expected_origin=...)`, or
`verify_feature_bounds(before, after, label, tolerance)`, or `verify_backed(backer,
feature, axis, label)`. Wrap a boolean when a no-op is plausible (computed offset,
off-center feature, emboss/deboss merge); skip trivially-overlapping ones. Declare a
mating area with `verify_backed` when a feature (standoff/boss/rib/ear) must be fully
backed by a specific named neighboring feature at one face — catches the recurring
mistake of reusing a centerline coordinate as a boundary, off by half the neighbor's
thickness; don't use it for a feature that legitimately overflows its base on other axes.
A failed assertion crashes the script; the wrapper reports it as a typed `silent_boolean`
/ `feature_overflow` / `workplane_drift` / `unbacked_mate` error naming the `label`.

**Geometry contract for scratch parts.** A part with no matching archetype and no
matching block (raw fluent CadQuery) must open with a named construction plan: each
stage asserted via `verify_stage(wp, label, bbox=..., vol_min=...)` before building
the next stage on top of it (`prompts/part.md` "Construction plan for scratch
geometry"). A failed stage is reported as a typed `stage_mismatch` error naming the
stage, so a wrong topology fails where it was introduced instead of surfacing as a
cryptic OCC error or a failed visual review several steps later.

## Measurement: telemetry + eval harness

1. **Telemetry is mandatory in the part loop** (Step 5): one record per attempt appended
   to `build/attempts.jsonl` via `src/telemetry.py`, append-only.
2. **Run the eval suite around any change to prompts/references/routing** — score the
   canonical corpus before/after and compare scorecards:
   `uv run --project "$SKILL_DIR" python "$SKILL_DIR/evals/run_evals.py" --run-dir <dir>`
   (add `--generate` for a fresh run; costs tokens). Reports first-shot rate,
   attempts-to-pass, Chamfer distance vs. golden mesh, cost/part — a regression here
   doesn't ship on vibes.

## Error handling reference

| Error type | Action |
|------------|--------|
| `non_manifold_edge` | Rebuild booleans; check zero-thickness faces |
| `non_watertight` | Open mesh holes: check unclosed boolean bodies |
| `disconnected_body` | Union split >1 component: union/bridge into one (`union`, `component_count`) |
| `dimension_mismatch` | Bbox beyond tolerance: fix the parameter driving that axis |
| `construction_error` | Boolean bodies don't overlap or faces are coincident (`Standard_ConstructionError`) |
| `command_not_done` | Boolean op failed: extend inner body >= 0.01mm past outer boundary (`BRep_API`) |
| `fillet_failure` | Fillet/chamfer left incomplete: radius exceeds an adjacent face (`StdFail_NotDone`) |
| `null_object` | Referenced a shape that doesn't exist: check selector strings/offsets (`Standard_NullObject`) |
| `index_out_of_range` | Check `pushPoints` list or loop bounds (`Standard_OutOfRange`) |
| `type_mismatch` | Wrong shape type for the operation: verify workplane/selector (`Standard_TypeMismatch`) |
| `occ_exception` | Unmapped OpenCASCADE error class: see hint for the exception class |
| `silent_boolean` | No-op boolean (`verify_boolean`): reposition tool to intersect body (`label`) |
| `feature_overflow` | Past base body (`verify_feature_bounds`): constrain/intersect with profile (`label`) |
| `workplane_drift` | Origin drifted (`check_workplane`): re-anchor with `.workplane(origin=...)` (`label`) |
| `stage_mismatch` | Construction stage bbox/volume off-plan (`verify_stage`): fix the stage named in `label`, not a later one |
| `unbacked_mate` | Feature's mating face not fully backed (`verify_backed`): extend the named neighbor to cover the face (`label`) |
| `thin_wall` | Below `wall_min_mm`: increase wall or reduce cutout |
| `overhang_exceeded` | Exceeds `overhang_max_deg`: chamfer, redesign, or warn |
| `visual_mismatch` | Checklist question answered "no": name it/the view, fix the parameter/geometry (`skill/phase3_build.md` Step 4) |

`visual_mismatch` is recorded by Claude in the part loop, not emitted by the wrapper; it
shares the 3-attempt retry budget with the geometry errors. After retries are exhausted,
ask the user how to proceed (different approach, a hint, or skip the part).

## Hardware dimension reference

Sizing tables for `heat_set_boss`, `counterbore_hole`, `countersink_hole`, and
`hex_nut_trap` live in `reference/hardware_dims.md`. **Read it before authoring any
part whose `blocks_needed` includes a fastener block** — never guess these dimensions.

## Gridfinity requests

When the request names Gridfinity (or asks for a part that must fit an existing Gridfinity
grid), **read `reference/gridfinity.md` before planning** — the 42 mm grid, 7 mm height
unit, foot profile, stacking lip, and magnet/screw geometry are a published standard, so
they are never researched, guessed, or hand-modelled. Build on the `gridfinity-bin` /
`gridfinity-baseplate` archetypes and the `blocks/gridfinity.py` blocks (`gridfinity_bin`,
`gridfinity_baseplate`, `gridfinity_feet`, `gridfinity_socket_cutter`); use
`gridfinity_feet` / `gridfinity_socket_cutter` to make any *other* part grid-compatible.
`src/gridfinity_check.py` verifies conformance and runs automatically in the quality gate
for parts that use these blocks.

## Quick reference: key files

| File | Role |
|------|------|
| `BUILD_PLAN.json` / `src/build_plan_schema.json` | Generated plan / its JSON Schema |
| `printer_profile.json` | Printer/material/nozzle/constraint defaults |
| `src/run_cadquery_model.py` / `quality_gate.py` | Geometry validator / DFM gate |
| `src/plan_validate.py` | Validates BUILD_PLAN.json vs. schema + inventory |
| `prompts/planning.md` / `prompts/part.md` | Prompt templates |
| `src/model_export.py` | Assembles unions into model.3mf + per-union/plate STL |
| `src/blocks/inventory.json` / `validate.py --search <kw>` | Block descriptors; lookup |
| `templates/archetypes.json` / `templates/*.py` | Known-good whole-part templates matched in Phase 3 Step 1.5 |
| `build/journal.md` | Append-only milestone log for resuming an interrupted run (see `skill/resume.md`) |
| `skill/*.md` | Setup and per-phase detail (see phase sections above) |
| `skill/resume.md` | Journal contract and interrupted-run resume procedure |
| `reference/hardware_dims.md` | Fastener sizing tables (block-gated, see above) |
| `reference/gridfinity.md` | Gridfinity standard: grid, profiles, holes (read on any Gridfinity request) |
| `src/gridfinity_check.py` | Gridfinity conformance check (auto-run by the gate for Gridfinity parts) |
| `reference/CadQuery Pattern Reference.md` / `Anti-Patterns.md` | Idioms + mistakes, every part |
| `reference/emboss_text.md` / `servo_splines.md` | Read only when needed |
| `reference/FDM 3D Print Design Guidelines.md` | Guidelines for planning + parts |
