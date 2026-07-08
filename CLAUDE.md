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
| `src/run_model_shim.py` | Tiny shim invoked by the wrapper: `runpy`-executes the model script and auto-exports its `result` to STL if the script did not export one itself. A `result` that is a `dict[str, Workplane]` (a multi-union part) is exported one `<union_id>.stl` per key. |
| `src/cq_verify.py` | Construction-time assertions a generated part script imports (visible on the wrapper's `PYTHONPATH`, like `blocks`): `verify_boolean` (silent no-op cut/union), `verify_feature_bounds` (feature past the base body), `check_workplane` (origin drift after `.center()`/`.hole()`). Each returns its post-op argument so it chains inline and raises one marked `RuntimeError` (`[cq-verify:<kind>:<label>] ...`) on failure, which `run_cadquery_model.py` maps to a typed `silent_boolean`/`feature_overflow`/`workplane_drift` error. CadQuery + stdlib only; not a block, not in `inventory.json`. |
| `src/units.py` | Shared part->unions expansion (no CadQuery import). `iter_unions(plan)` yields `(part, union_id, plate)` for every union; `resolve_unions(part, result)` normalizes a script's `result` (a `Workplane` -> one union id=part id, or a `dict[str, Workplane]` -> one per key, keys validated against declared `unions`), ignoring the reserved `keep_out` key. `resolve_keep_out(part, result)` extracts that reserved key's `name -> Workplane` mapping of author-declared keep-out zones (never itself a union); `keep_out_stl_name(part_id, zone_name)` is the shared writer/reader STL naming convention. `iter_kinematics_entries(kinematics)` flattens the `kinematics` tree (entries nest via `children`), depth-first; also used to collect one entry's own swept subtree via `iter_kinematics_entries([entry])`. The one place that knows a part may produce several unions (or zones); used by `model_export`, `plan_validate`, `kinematic_check`, `plate_clearance_check`, `keep_out_check`, `build_template`. |
| `src/quality_gate.py` | Aggregates wrapper DFM + in-process trimesh geometry/overhang analysis (watertightness, overhang area/worst-angle/location vs `overhang_max_deg`); no slicer or MCP required. Also runs the kinematic, plate-clearance, keep-out-zone, edge-treatment (chamfer/fillet), and cosmetic-slope (visual_quality-only, advisory) stages once outside the fix loop. Emits structured report; invokes `claude -p` for targeted fixes (up to 2 rounds); emits print recipe on clean pass. Sets `PYTHONPATH=<src>` itself. Real slicer-based printability validation (e.g. the orca-check MCP) is optional and external, not part of the gate. |
| `src/plan_validate.py` | Validates `BUILD_PLAN.json` against JSON Schema draft-7; cross-checks `blocks_needed` against `blocks/inventory.json`, part `placement` rotation axes, union-id uniqueness across the model (a part's declared `unions`, else its id), `kinematics` entries at every nesting depth of their `children` tree (`moving_union` is a **union** id; referenced block exists, carries a `dof`; joint contract type/axis satisfied), and `joints` entries (members reference the block's declared `emits` ids and existing parts; the mate graph is a single tree rooted at `root_part`, catching unanchored, double-anchored, and conflicting-mate-path parts). |
| `src/printer_profile_validate.py` | Validates `printer_profile.json` against `src/printer_profile_schema.json` (`validate_profile`); `write_profile_fields` merges a partial field update (e.g. an override the user stated for one model) into the file and re-validates before writing. CLI: `python printer_profile_validate.py printer_profile.json` to validate, `--set field=value` (dotted for `constraints.*`) to write back. |
| `src/placement.py` | Shared assembled-frame placement helper: builds a 4x4 transform (`to_matrix`, for trimesh/3MF) and positions a CadQuery Workplane (`apply_cq`) from a part `placement` (ordered X/Y/Z rotations through origin, then translation), or from a general 4x4 transform (`apply_matrix`, for a derived mate-chain pose that doesn't decompose back into the ordered-rotation shape). Identity when absent. |
| `src/mate_chain.py` | Derives a mated part's assembled-frame pose from `BUILD_PLAN.json`'s `joints` + `root_part`: `compute_mate_poses(plan)` walks the mate chain outward from `root_part`, composing `world_pose(part_B) = world_pose(part_A) @ dock_A @ inverse(dock_B)` at each hop (both members of a matched-pair block share one local frame with exactly one embedding into the assembled frame, so this is exact, not solved for). Returns `{part_id: 4x4 transform}` for every non-root part reached via a joint; trusts `plan_validate`'s mate-graph tree check (no cycle handling here). |
| `src/model_export.py` | Model-level export: loads each part's `result`, splits it into unions via `units.resolve_unions` (a part may declare `unions` and return a `dict[str, Workplane]`; default is one union id=part id), applies the part's `placement` to each union -- or, for a part reached via a `joints` mate chain, its derived pose from `mate_chain.compute_mate_poses` instead -- and emits one named-object `model.3mf` into `model_dir` (each **union** a separately, uniquely named object with per-union `plate` metadata; duplicate descriptions are disambiguated by suffixing the union id), one assembled-pose STL per union (the kinematic check's input) and one fused STL per multi-union plate into `stl_dir` (keyword-only, defaults to `model_dir` when omitted). Also extracts any declared keep-out zones (`units.resolve_keep_out`), poses each the same way as its declaring part's unions, and writes one assembled-pose STL per zone (`units.keep_out_stl_name`) into `stl_dir` -- returned as `keep_out_stls`, but never written to the 3MF, a plate, or a per-union STL. Uses `exporters/threemf_multi.py`. |
| `src/build_template.py` | Deliverable build-script template, copied verbatim (no placeholder substitution) to `build/build.py`; its tooling imports (`exporters/`, `blocks/`, `mesh_io.py`, `model_export.py`, `print_orientation.py`, `placement.py`, `mate_chain.py`, `units.py`) are bundled into a sibling `lib/` directory, which it adds to `sys.path` itself. Running `python build/build.py` regenerates the deliverables with objects in print orientation: reuses `build/orientations.json` when present, recomputes via `print_orientation.py` otherwise, then calls `model_export.export_model` -- `model.3mf` defaults to the project root, STLs to `stl/`. Standalone; not invoked by the rest of the pipeline. |
| `src/kinematic_check.py` | Whole-model kinematic validation: for each plan `kinematics` entry, at every nesting depth of its `children` tree, checks `required_range` (relative to the union's authored pose; may be negative/straddle zero; per-bound `lo_inclusive`/`hi_inclusive`) against the block's nominal `dof.mechanical_limit`, then sweeps the entry's swept subtree (`moving_union` plus every union nested under its `children`, carried along rigidly by the same transform) against every union **outside that subtree** (each a separately named collision object) with trimesh + python-fcl, reporting the binding value and `colliding_union`. Print-in-place joints are swept like any other (no special case). Emits the shared `{source, severity, type, message, hint}` contract. Requires `python-fcl` and `scipy`; degrades to a `check_skipped` warning otherwise. |
| `src/plate_clearance_check.py` | Whole-model plate-clearance validation: for each plate holding more than one union, measures the minimum surface gap between every pair of co-plated unions on their assembled-pose STLs and flags any pair whose gap is at or below one layer height (`nozzle_mm * 0.5`), which would fuse them in the print. Measures in the assembled pose because the plate is fused as a rigid cluster (distance-preserving rotation). Emits the shared `{source, severity, type, message, hint}` contract with `type: "plate_clearance"`, `severity: "error"`; degrades to a `check_skipped` warning when trimesh/python-fcl are unavailable. |
| `src/keep_out_check.py` | Whole-model keep-out-zone validation: discovers every declared zone's assembled-pose STL in `--stl-dir` via the `keep_out__<part_id>__<zone_name>.stl` naming convention (`units.keep_out_stl_name`) `model_export` writes, then intersects each zone against every union **excluding the zone's own declaring part's unions** (trimesh + python-fcl, same tooling as `kinematic_check.py`). Emits the shared `{source, severity, type, message, hint}` contract with `type: "keep_out_violation"`, `severity: "error"`, naming the offending union and the `(zone_part, zone_name)` pair; degrades to a `check_skipped` warning when trimesh/python-fcl are unavailable, or when a foreign union's STL is missing. Returns `[]` (no import attempt) when the model declares no zones. |
| `src/edge_treatment_check.py` | Per-part Chamfer / Fillet rule enforcement (horizontal edge -> chamfer, vertical edge -> fillet). Inspects the treatment at apply-time rather than reverse-engineering it from a mesh: wraps `cq.Workplane.fillet`/`.chamfer` and re-runs the part script (`exporters._load_result`) to record the exact BRep tangent + midpoint of every treated edge (faces expand to their edges; round features never enter a fillet/chamfer call, so no false positives), attributes each edge to its union by bbox, then classifies it **in the print frame** -- the bed-relative frame where the rule matters -- by rotating its authored-frame tangent through the union's print orientation via `placement.transform_direction`. A fillet on a horizontal edge and a chamfer on a vertical edge are advisory findings; diagonal edges and tilted round rims are passed silently. Emits the shared `{source, severity, type, message, hint}` contract with `source`/`type` `"edge_treatment"`, `severity: "warning"` (a print-quality preference, not a hard failure -- the harmful half, a bottom-edge fillet past the overhang limit, is already caught by the overhang check). A treated union with no supplied print orientation is reported as `check_skipped` (never classified in the authored frame, since that is the wrong frame for a bed-relative rule); also degrades to `check_skipped` if CadQuery is unavailable. |
| `src/feature_presence_check.py` | Per-part feature-presence validation: asserts that every `interfaces[]` entry declaring a structured `position_mm` (and optional `diameter_mm`/`size_mm`) was actually built at that position. Captures placement at construction time -- wraps `cq.Workplane.cut`/`.union` and re-runs the part script (`exporters._load_result`, the `edge_treatment_check` pattern) to record each positioned tool's authored-frame bbox center + extents (interface blocks return unpositioned solids, so the placement is captured at the boolean that applies them, not by hooking the block). Matches declared interfaces against the recorded features: no feature within `_POS_TOL_MM` of a declared position is a blocking `feature_absent` error; a nearest match beyond `_DRIFT_TOL_MM` in center, or a declared size absent from the feature's extents, is an advisory `feature_drift` warning. Only block-emitted types (`port_cutout`, `cable_slot`, `vent_grid`, `screw_boss`, `pcb_standoff`) are asserted; any other type or a non-re-runnable script is `check_skipped`, never a false `feature_absent`. The in-place hole family is out of first scope. The deterministic backstop beneath the visual per-feature review question. Wired into `quality_gate.py` as a once-outside-the-fix-loop stage. |
| `src/measure_stl.py` | Geometry feature extractor: detects bounding box, horizontal layers, vertical cylindrical features, and thin regions (local ray-cast wall thickness, classified thin-in-XY vs thin-in-Z) from an STL using trimesh + numpy. Emits structured JSON. |
| `src/preview.py` | Headless preview renderer using CadQuery tessellation + matplotlib (Agg backend) -> multi-view PNG. No OpenGL or display server required. |
| `src/render_preview.py` | Subprocess entry point for previews: runs a model script in an isolated namespace, captures `result`, calls `preview.render_multi_view`/`render_single`. |
| `src/mesh_io.py` | Thin trimesh loader with watertightness validation. Also the shared geometry primitives on a posed mesh: `overhang_metrics`/`support_cost` (down-facing overhang), and `up_facing_incline_area` (up-facing gentle-incline/cosmetic-slope area in a degree band, used by `print_orientation` and surfaced by the gate's cosmetic-slope stage). trimesh + numpy only, no matplotlib. |

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

## File Layout

```
.
  src/
    run_cadquery_model.py    # Model runner / DFM wrapper (emits JSON contract)
    run_model_shim.py        # runpy shim that auto-exports `result` to STL
    quality_gate.py          # DFM + geometry/overhang aggregation, claude -p fixes
    plan_validate.py         # BUILD_PLAN.json schema + inventory cross-check
    printer_profile_validate.py # printer_profile.json schema validation + field write-back
    kinematic_check.py       # Whole-model range-of-motion sweep (trimesh + fcl)
    plate_clearance_check.py # Whole-model co-plated union clearance check (trimesh + fcl)
    keep_out_check.py        # Whole-model keep-out-zone check (trimesh + fcl)
    edge_treatment_check.py  # Per-part chamfer/fillet rule check (apply-time hook + build-frame classify)
    placement.py             # Assembled-frame placement helper (cq + trimesh)
    mate_chain.py            # Derived pose along a `joints` mate chain from root_part
    units.py                 # Part->unions / keep-out-zone expansion (resolve_unions / resolve_keep_out)
    model_export.py          # Model-level export: named 3MF + per-union/plate/keep-out-zone STL
    build_template.py        # build.py template copied to build/; regenerates plates in print orientation
    measure_stl.py           # Geometry feature extractor (trimesh + numpy)
    preview.py               # CadQuery tessellation + matplotlib preview renderer
    render_preview.py        # Subprocess entry point for preview.py
    mesh_io.py               # Trimesh loader + watertightness validation
    build_plan_schema.json   # JSON Schema draft-7 for BUILD_PLAN.json
    printer_profile_schema.json  # JSON Schema draft-7 for printer_profile.json
    printer_profile.default.json # Default printer_profile.json seeded into a fresh directory

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
    test_printer_profile_validate.py # printer_profile.json schema + write-back -- fast, no CadQuery
    test_edge_treatment_check.py     # Chamfer/fillet rule check (CadQuery)
    fixtures/
```
