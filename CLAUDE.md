# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **cq-design** Claude Code skill. It generates parametric 3D models
using [CadQuery](https://cadquery.readthedocs.io/) (Python) via the pipeline:
Sourcing Triage -> Planning -> Part Loop -> Model Export -> Quality Gate.

The skill definition lives in `SKILL.md` (trigger, contracts, and per-phase pointers)
with phase detail split into `skill/phase1_requirements.md` through
`skill/phase4_deliver.md`, plus `skill/phase0_sourcing.md` and `skill/setup.md`,
read on demand as each phase starts.
Claude itself drives
the pipeline inline (reads `BUILD_PLAN.json`, writes each part script, runs the tool
scripts via Bash, iterates on errors) -- there is no `orchestrate.py` script. The
Python files under `src/` are the tool boundaries Claude calls. This CLAUDE.md covers
development of those scripts.

Phase 1-3 LLM roles (dimension research, planning, and autonomous part authoring) may
execute in sub-agents rather than inline in the main session -- see `ARCHITECTURE.md`
for the agent roster and `skill/phase1_requirements.md` / `skill/phase2_planning.md` /
`skill/phase3_build.md` for the invocation, return-contract, and escalation details.
The agent-routing gate itself (autonomous vs. progressive per part) lives in
`skill/phase3_build.md`'s Agent routing gate section; user checkpoints always stay in
the main session regardless of routing.

## Python Version Constraint

**Python 3.10-3.12 only.** CadQuery's OpenCASCADE (OCC) kernel has no wheels for 3.13+.
This is enforced by `requires-python` in `pyproject.toml`; uv handles version selection automatically.

## Setup

```bash
uv sync
```

Python 3.12 is pinned in `.python-version`. uv downloads it if not present.

To update the `cq-warehouse` git dep: `uv lock --upgrade-package cq-warehouse`

## Running Tests

```bash
# Full suite (CadQuery tests are slow -- a few seconds per file)
uv run pytest tests/

# Single file
uv run pytest tests/test_run_wrapper.py

# Single test
pytest tests/test_run_wrapper.py::test_happy_path

# Fast subset (plan validate -- no CadQuery)
uv run pytest tests/test_plan_validate.py
```

`test_plan_validate.py` only exercises JSON Schema validation and runs in well under a
second with no CadQuery installation. All other test files are integration tests that
run real CadQuery scripts (a few seconds each).

## Core Scripts

One-line index below; File Layout has the same short form organized by directory.
**Full per-script contract detail** (JSON shapes, CLI flags, typed error names, edge
cases) lives in [reference/scripts.md](reference/scripts.md) -- read it before modifying
or calling any script.

| Script | Role |
|--------|------|
| `src/run_cadquery_model.py` | Model runner / DFM wrapper (emits JSON contract) |
| `src/run_model_shim.py` | runpy shim that auto-exports `result` to STL |
| `src/cq_verify.py` | Construction-time assertions (`verify_boolean`, `verify_feature_bounds`, `check_workplane`, `verify_stage`, `verify_backed`) |
| `src/script_lint.py` | AST-based pre-flight lint for a generated part script (stdlib only) |
| `src/units.py` | Part->unions / keep-out-zone expansion |
| `src/quality_gate.py` | DFM + geometry/overhang aggregation, `claude -p` fixes |
| `src/plan_validate.py` | `BUILD_PLAN.json` schema + inventory cross-check |
| `src/printer_profile_validate.py` | `printer_profile.json` schema validation + field write-back |
| `src/import_params.py` | Reconcile a part script's `PARAMETERS` block back into `BUILD_PLAN.json` |
| `src/placement.py` | Assembled-frame placement helper (cq + trimesh) |
| `src/mate_chain.py` | Derived pose along a `joints` mate chain from `root_part` |
| `src/model_export.py` | Model-level export: named 3MF + per-union/plate/keep-out-zone STL |
| `src/build_template.py` | `build.py` template; regenerates plates in print orientation |
| `src/kinematic_check.py` | Whole-model range-of-motion sweep (trimesh + fcl) |
| `src/plate_clearance_check.py` | Whole-model co-plated union clearance check (trimesh + fcl) |
| `src/keep_out_check.py` | Whole-model keep-out-zone check (trimesh + fcl) |
| `src/freshness.py` | Provenance stamp: hash a part script, compare/write the export manifest |
| `src/interference.py` | Shared static interference primitive (trimesh + fcl + manifold3d) |
| `src/edge_treatment_check.py` | Per-part chamfer/fillet rule check (apply-time hook + build-frame classify) |
| `src/gridfinity_check.py` | Per-part Gridfinity conformance check (grid, height, foot profile, mating) |
| `src/feature_presence_check.py` | Per-part `interfaces[]` position assertion |
| `src/telemetry.py` | Append-only per-attempt log -> `build/attempts.jsonl` |
| `src/request_log_search.py` | Search `BUILD_PLAN.json`'s `request_log` by keyword/kind |
| `src/print_orientation.py` | Computes bed-relative print orientation by minimizing support/overhang cost |
| `src/minimal_cutout_search.py` | Bisects a part-script parameter to the minimal value clearing a kinematics entry's required range |
| `src/convert_build123d.py` | Phase 0 sourcing aid: build123d -> CadQuery conversion |
| `src/cq_compat.py` | Compatibility shim neutralizing a `cq_warehouse` shape-copy patch |
| `src/init_permissions.py` | Seeds a working directory's `.claude/settings.local.json` (permission patterns + the session-cost `Stop` hook) |
| `src/session_cost.py` | Records billed token cost from the session transcript -> `build/cost.json` (hook-driven, stdlib only) |
| `evals/run_evals.py` | Eval harness (score-only by default; `--generate` opt-in) |
| `src/measure_stl.py` | Geometry feature extractor (trimesh + numpy) |
| `src/preview.py` | CadQuery tessellation + matplotlib preview renderer |
| `src/render_preview.py` | Subprocess entry point for `preview.py` |
| `src/mesh_io.py` | Trimesh loader + watertightness validation |

## Key Constraints

- **JSON contract**: `run_cadquery_model.py` always emits `success`, `errors`, `geometry`,
  `stl`, `stls`, `preview`, `previews`, `watertight`, `stdout`, `stderr`, `returncode`.
  Do not rename or remove keys — Claude parses them inline during the part loop.
- **`errors` field**: always present, empty list on a clean run. Each entry has `type`,
  `message`, `hint`. Claude uses these typed errors to build structured correction prompts.
- **Multi-union parts**: when a script's `result` is a `dict[str, Workplane]`, the wrapper
  validates each union body; its findings carry a `union` field and the `message` is prefixed
  with the union id, and the `geometry` block aggregates over the unions (summed volume/faces,
  bbox envelope). A single-`Workplane` result is byte-identical to the single-body report.
- **Thin-interface check** (`--wall-min` set): the `geometry` block gains `thin_regions`
  (each with `thickness_mm`, `orientation` of `xy`/`z`, `location_xyz_mm`, `thin_direction`,
  `nearest_feature`). Only XY-thin regions below `wall_min` become `thin_interface` errors;
  Z-thin slabs are reported in `geometry` but are benign for printing (advisory only).
- **STL hidden during iteration**: scripts run in `tempfile.mkdtemp()`. STL paths are
  `null`/`[]` in normal JSON output. Use `--deliver --formats stl,...` to get output files.
- **Exit codes**: 0 = success, 1 = failure, 2 = interpreter not found, 3 = timeout.
- **PYTHONPATH**: `run_cadquery_model.py` and `quality_gate.py` each set
  `PYTHONPATH=<src_dir>` on the model subprocess so generated scripts can
  `from blocks import fillet_box` without any path manipulation. Tests do the same via
  `conftest.py` (`sys.path.insert(0, src)`).
- **Block imports**: Always import from `blocks` (the package), not from individual
  submodules. Claude writes the `from blocks import ...` lines directly when generating
  part scripts (no automatic import injection).
- **`build/cost.json`**: written by the `session_cost.py` `Stop` hook (seeded by
  `init_permissions.py`), not by the pipeline. It is a cumulative billed-cost record
  keyed by session id, safe to delete, and must not be bundled into `lib/` or a
  deliverable. The eval scorecard reads it as a cost source; nothing else depends on it.

## File Layout

```
.
  src/
    run_cadquery_model.py    # Model runner / DFM wrapper (emits JSON contract)
    run_model_shim.py        # runpy shim that auto-exports `result` to STL
    quality_gate.py          # DFM + geometry/overhang aggregation, claude -p fixes (model from skill_config.json's models.fix_loop)
    plan_validate.py         # BUILD_PLAN.json schema + inventory cross-check
    script_lint.py           # AST-based pre-flight lint for a generated part script (stdlib only)
    printer_profile_validate.py # printer_profile.json schema validation + field write-back
    import_params.py         # Reconcile a part script's PARAMETERS block back into BUILD_PLAN.json
    kinematic_check.py       # Whole-model range-of-motion sweep (trimesh + fcl)
    minimal_cutout_search.py # Bisects a part-script parameter to the minimal value clearing a kinematics entry
    plate_clearance_check.py # Whole-model co-plated union clearance check (trimesh + fcl)
    keep_out_check.py        # Whole-model keep-out-zone check (trimesh + fcl)
    edge_treatment_check.py  # Per-part chamfer/fillet rule check (apply-time hook + build-frame classify)
    gridfinity_check.py      # Per-part Gridfinity conformance check (grid/height/foot profile/mating; auto-scoped gate stage)
    placement.py             # Assembled-frame placement helper (cq + trimesh)
    mate_chain.py            # Derived pose along a `joints` mate chain from root_part
    units.py                 # Part->unions / keep-out-zone expansion (resolve_unions / resolve_keep_out)
    freshness.py              # Provenance stamp: hash a part script, compare/write the export manifest
    model_export.py          # Model-level export: named 3MF + per-union/plate/keep-out-zone STL
    build_template.py        # build.py template copied to build/; regenerates plates in print orientation
    telemetry.py             # Append-only per-attempt log -> build/attempts.jsonl
                              # (build/journal.md is a milestone log the orchestrator appends to
                              # directly per skill/resume.md -- no dedicated script)
    session_cost.py          # Session transcript -> billed token cost in build/cost.json (Stop hook)
    request_log_search.py    # Search BUILD_PLAN.json's request_log by keyword/kind
    measure_stl.py           # Geometry feature extractor (trimesh + numpy)
    preview.py               # CadQuery tessellation + matplotlib preview renderer
    render_preview.py        # Subprocess entry point for preview.py
    mesh_io.py               # Trimesh loader + watertightness validation
    build_plan_schema.json   # JSON Schema draft-7 for BUILD_PLAN.json
    printer_profile_schema.json  # JSON Schema draft-7 for printer_profile.json
    printer_profile.default.json # Default printer_profile.json seeded into a fresh directory
    skill_config.default.json # Default skill_config.json (models.planner/part_author/fix_loop) seeded into a fresh directory

    blocks/
      __init__.py            # Re-exports all blocks
      primitives.py          # fillet_box, hollow_box
      fasteners.py           # screw_boss, pcb_standoff, snap hooks, alignment pins
      connectors.py          # port_cutout, cable_slot, vent_grid
      hardware.py            # cq_warehouse-backed fastener geometry
      joints.py              # dovetail_groove / dovetail_tongue sliding joints
      gridfinity.py          # Gridfinity bins, baseplates, feet, socket cutters (42 mm grid standard)
      inventory.json         # Machine-readable block descriptors
      inventory_schema.json  # JSON Schema for inventory.json
      validate.py            # Inventory loader + validator

    exporters/
      __init__.py            # run_exporters(script, formats, output_dir)
      stl.py step.py threemf.py obj.py iges.py scad.py
      threemf_multi.py       # Multi-object 3MF writer (named unions + plate metadata)

  evals/
    cases/<case>/        # request.md, golden BUILD_PLAN.json, golden/*.stl, case.json
    run_evals.py         # Scorecard runner (score-only by default; --generate opt-in)
    generate_goldens.py  # Regenerates the golden STLs
    model_prices.json    # Editable USD-per-MTok table for cost estimates

  prompts/
    planning.md          # Planning phase prompt (outputs BUILD_PLAN.json)
    part.md              # Per-part code generation prompt

  templates/
    archetypes.json         # Machine-readable archetype index (name, file, use, params)
    archetypes_schema.json  # JSON Schema for archetypes.json
    enclosure_body.py, lid_sliding.py, lid_snap.py, lid_screwed.py,
    adapter_ring_flanged.py, l_bracket_gusset.py, plate_boss_pattern.py,
    hook.py, clip.py, stand.py,
    gridfinity_bin.py, gridfinity_baseplate.py   # Known-good, pre-verified whole-part templates,
                                    # one per archetype (Phase 3 Step 1.5 match source)

  skill/                 # Per-phase SKILL.md detail (setup, phase0-4, resume), read on demand
  reference/             # Injected design references (CadQuery patterns, FDM DFM, hardware_dims)
  openspec/              # OpenSpec specs and change history

  tests/
    conftest.py                      # Adds src/ to sys.path; CadQuery fixtures
    test_blocks.py                   # Block geometry (CadQuery)
    test_run_wrapper.py              # run_cadquery_model.py JSON contract
    test_exporters.py                # Modular exporters (CadQuery)
    test_preview.py                  # preview.py / render_preview.py
    test_mesh_io.py                  # Trimesh loader
    test_stl_to_3mf.py               # 3MF export path
    test_cq_warehouse_integration.py # cq_warehouse fastener integration
    test_plan_validate.py            # Schema validation -- fast, no CadQuery
    test_freshness.py                # Provenance stamp hash/compare/manifest -- fast, no CadQuery
    test_script_lint.py              # AST pre-flight lint findings + CLI -- fast, no CadQuery
    test_telemetry.py                # Attempt-log helper + CLI -- fast, no CadQuery
    test_request_log_search.py       # request_log filter helper + CLI -- fast, no CadQuery
    test_run_evals.py                # Eval runner scoring path -- fast, no CadQuery
    test_eval_corpus.py              # Corpus sanity: plans validate, goldens match dims
    test_printer_profile_validate.py # printer_profile.json schema + write-back -- fast, no CadQuery
    test_import_params.py            # import_params.py parse/reconcile/write-back -- fast, no CadQuery
    test_edge_treatment_check.py     # Chamfer/fillet rule check (CadQuery)
    test_gridfinity.py               # Gridfinity blocks + conformance check (CadQuery)
    test_minimal_cutout_search.py    # Parameter bisection search against a kinematics entry (CadQuery)
    test_templates.py                # Archetype index validation + per-template lint/geometry
    fixtures/
```
