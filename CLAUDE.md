# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **cq-design** Claude Code skill. It generates parametric 3D models
using [CadQuery](https://cadquery.readthedocs.io/) (Python) via the pipeline:
Planning -> Part Loop -> Assembly -> Quality Gate.

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
| `src/quality_gate.py` | Aggregates wrapper DFM + in-process trimesh geometry/overhang analysis (watertightness, overhang area/worst-angle/location vs `overhang_max_deg`); no slicer or MCP required. Emits structured report; invokes `claude -p` for targeted fixes (up to 2 rounds); emits print recipe on clean pass. Sets `PYTHONPATH=<src>` itself. Real slicer-based printability validation (e.g. the orca-check MCP) is optional and external, not part of the gate. |
| `src/plan_validate.py` | Validates `BUILD_PLAN.json` against JSON Schema draft-7; cross-checks `blocks_needed` against `blocks/inventory.json`, and `kinematics` entries against part ids and the referenced block's `dof` (existence + matching `unit`). |
| `src/kinematic_check.py` | Kinematic range-of-motion validation: for each plan `kinematics` entry, checks the declared `required_range` against the block's nominal `dof.mechanical_limit`, then sweeps the moving part's STL through that range against the fixed part with trimesh + python-fcl (scipy-backed), flagging the binding value. Emits the shared `{source, severity, type, message, hint}` issue contract. Requires `python-fcl` and `scipy`; degrades to a `check_skipped` warning otherwise. |
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

  prompts/
    planning.md          # Planning phase prompt (outputs BUILD_PLAN.json)
    part.md              # Per-part code generation prompt
    assembly.md          # Assembly phase prompt

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
