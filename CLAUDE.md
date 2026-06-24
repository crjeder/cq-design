# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **cq-design** Claude Code skill. It generates parametric 3D models
using [CadQuery](https://cadquery.readthedocs.io/) (Python) via the pipeline:
Planning -> Part Loop -> Model Export -> Quality Gate.

The skill definition and phase descriptions live in `SKILL.md`. Claude itself drives
the pipeline inline (reads `BUILD_PLAN.json`, writes each part script, runs the tool
scripts via Bash, iterates on errors) -- there is no `orchestrate.py` script. The
Python files under `src/` are the tool boundaries Claude calls. This CLAUDE.md covers
development of those scripts.

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

| Script | Role |
|--------|------|
| `src/run_cadquery_model.py` | Subprocess wrapper: runs a `.py` model (via `run_model_shim.py`), validates geometry, checks DFM constraints, emits structured JSON with `errors` and `geometry` fields. STL paths are hidden during iteration (temp dir); use `--deliver` to get deliverable files. Sets `PYTHONPATH=<src>` itself so the model can `from blocks import ...`. |
| `src/run_model_shim.py` | Tiny shim invoked by the wrapper: `runpy`-executes the model script and auto-exports its `result` Workplane to STL if the script did not export one itself. |
| `src/quality_gate.py` | Aggregates wrapper DFM + in-process trimesh geometry/overhang analysis (watertightness, overhang area/worst-angle/location vs `overhang_max_deg`); no slicer or MCP required. Also runs the kinematic and plate-clearance stages once outside the fix loop. Emits structured report; invokes `claude -p` for targeted fixes (up to 2 rounds); emits print recipe on clean pass. Sets `PYTHONPATH=<src>` itself. Real slicer-based printability validation (e.g. the orca-check MCP) is optional and external, not part of the gate. |
| `src/plan_validate.py` | Validates `BUILD_PLAN.json` against JSON Schema draft-7; cross-checks `blocks_needed` against `blocks/inventory.json`, part `placement` rotation axes, and `kinematics` entries (`moving_union` is a part id; referenced block exists, carries a `dof`, and `unit` matches). |
| `src/placement.py` | Shared assembled-frame placement helper: builds a 4x4 transform (`to_matrix`, for trimesh/3MF) and positions a CadQuery Workplane (`apply_cq`) from a part `placement` (ordered X/Y/Z rotations through origin, then translation). Identity when absent. |
| `src/model_export.py` | Model-level export: loads each union's `result`, applies its `placement`, and emits one named-object `model.3mf` (each union a separately named object with `plate` metadata), one assembled-pose STL per union (the kinematic check's input), and one fused STL per multi-union plate. Uses `exporters/threemf_multi.py`. |
| `src/build_template.py` | Deliverable build-script template. The skill copies it to `build/build.py`, substituting the `{{SKILL_SRC}}` placeholder with its `src/` path. Running `python build/build.py` regenerates all plates with objects in print orientation: reuses `build/orientations.json` when present, recomputes via `print_orientation.py` otherwise, then calls `model_export.export_model`. Standalone; not invoked by the rest of the pipeline. |
| `src/kinematic_check.py` | Whole-model kinematic validation: for each plan `kinematics` entry, checks `required_range` (relative to the union's authored pose; may be negative/straddle zero; per-bound `lo_inclusive`/`hi_inclusive`) against the block's nominal `dof.mechanical_limit`, then sweeps the `moving_union`'s assembled STL against **every other union** (each a separately named collision object) with trimesh + python-fcl, reporting the binding value and `colliding_union`. Print-in-place joints are swept like any other (no special case). Emits the shared `{source, severity, type, message, hint}` contract. Requires `python-fcl` and `scipy`; degrades to a `check_skipped` warning otherwise. |
| `src/plate_clearance_check.py` | Whole-model plate-clearance validation: for each plate holding more than one union, measures the minimum surface gap between every pair of co-plated unions on their assembled-pose STLs and flags any pair whose gap is at or below one layer height (`nozzle_mm * 0.5`), which would fuse them in the print. Measures in the assembled pose because the plate is fused as a rigid cluster (distance-preserving rotation). Emits the shared `{source, severity, type, message, hint}` contract with `type: "plate_clearance"`, `severity: "error"`; degrades to a `check_skipped` warning when trimesh/python-fcl are unavailable. |
| `src/measure_stl.py` | Geometry feature extractor: detects bounding box, horizontal layers, vertical cylindrical features, and thin regions (local ray-cast wall thickness, classified thin-in-XY vs thin-in-Z) from an STL using trimesh + numpy. Emits structured JSON. |
| `src/preview.py` | Headless preview renderer using CadQuery tessellation + matplotlib (Agg backend) -> multi-view PNG. No OpenGL or display server required. |
| `src/render_preview.py` | Subprocess entry point for previews: runs a model script in an isolated namespace, captures `result`, calls `preview.render_multi_view`/`render_single`. |
| `src/mesh_io.py` | Thin trimesh loader with watertightness validation. trimesh + numpy only, no matplotlib. |

## Key Constraints

- **JSON contract**: `run_cadquery_model.py` always emits `success`, `errors`, `geometry`,
  `stl`, `stls`, `preview`, `previews`, `watertight`, `stdout`, `stderr`, `returncode`.
  Do not rename or remove keys — Claude parses them inline during the part loop.
- **`errors` field**: always present, empty list on a clean run. Each entry has `type`,
  `message`, `hint`. Claude uses these typed errors to build structured correction prompts.
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

## File Layout

```
.
  src/
    run_cadquery_model.py    # Model runner / DFM wrapper (emits JSON contract)
    run_model_shim.py        # runpy shim that auto-exports `result` to STL
    quality_gate.py          # DFM + geometry/overhang aggregation, claude -p fixes
    plan_validate.py         # BUILD_PLAN.json schema + inventory cross-check
    kinematic_check.py       # Whole-model range-of-motion sweep (trimesh + fcl)
    placement.py             # Assembled-frame placement helper (cq + trimesh)
    model_export.py          # Model-level export: named 3MF + per-union/plate STL
    build_template.py        # build.py template copied to build/; regenerates plates in print orientation
    measure_stl.py           # Geometry feature extractor (trimesh + numpy)
    preview.py               # CadQuery tessellation + matplotlib preview renderer
    render_preview.py        # Subprocess entry point for preview.py
    mesh_io.py               # Trimesh loader + watertightness validation
    build_plan_schema.json   # JSON Schema draft-7 for BUILD_PLAN.json

    blocks/
      __init__.py            # Re-exports all blocks
      primitives.py          # fillet_box, hollow_box
      fasteners.py           # screw_boss, pcb_standoff, snap hooks, alignment pins
      connectors.py          # port_cutout, cable_slot, vent_grid
      hardware.py            # cq_warehouse-backed fastener geometry
      joints.py              # dovetail_groove / dovetail_tongue sliding joints
      inventory.json         # Machine-readable block descriptors
      inventory_schema.json  # JSON Schema for inventory.json
      validate.py            # Inventory loader + validator

    exporters/
      __init__.py            # run_exporters(script, formats, output_dir)
      stl.py step.py threemf.py obj.py iges.py scad.py
      threemf_multi.py       # Multi-object 3MF writer (named unions + plate metadata)

  prompts/
    planning.md          # Planning phase prompt (outputs BUILD_PLAN.json)
    part.md              # Per-part code generation prompt

  reference/             # Injected design references (CadQuery patterns, FDM DFM)
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
    fixtures/
```
