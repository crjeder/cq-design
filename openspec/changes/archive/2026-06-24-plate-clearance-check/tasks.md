## 1. Clearance stage module

- [x] 1.1 Add `src/plate_clearance_check.py` with `run_plate_clearance_check(plan, stl_dir) -> list[dict]`. Derive plate membership the same way `model_export._plate_of` does (explicit `plate`, else part `id`); build `{plate: [union_id, ...]}` and keep only plates with more than one union.
- [x] 1.2 Compute the threshold as `plan["nozzle_mm"] * 0.5` (one layer height), matching `quality_gate.py:218`'s `layer_height_mm` derivation.
- [x] 1.3 Load each co-plated union's assembled-pose STL from `stl_dir` (the per-union meshes the kinematic stage consumes) via trimesh; for each unordered pair compute the minimum surface-to-surface distance using python-fcl (through `trimesh.collision`), and flag pairs where `gap <= threshold`.
- [x] 1.4 Emit one `{source: "geometry", severity: "error", type: "plate_clearance", message, hint, plate, union_a, union_b, gap_mm, threshold_mm}` issue per failing pair. No issue for passing pairs or single-union plates.
- [x] 1.5 Wrap the trimesh/fcl import in the same degrade pattern as `kinematic_check.py`: on ImportError emit one `{severity: "warning", type: "check_skipped"}` issue and return without raising.

## 2. Wire into the gate

- [x] 2.1 Add `_run_plate_clearance_stage(plan, stl_dir)` to `quality_gate.py` mirroring `_run_kinematic_stage` (`:299`): no-op when no plate holds more than one union, else import and call `run_plate_clearance_check`.
- [x] 2.2 Call the stage once, outside the fix loop, next to the kinematic stage (`quality_gate.py:424-425`), appending its issues to `all_issues`.

## 3. Tests

- [x] 3.1 `tests/test_plate_clearance_check.py`: two unions on one plate separated by less than one layer height -> one `plate_clearance` error naming both unions and the plate.
- [x] 3.2 Same two unions separated by more than one layer height -> no issue.
- [x] 3.3 Gap exactly at one layer height -> flagged (at-or-below boundary).
- [x] 3.4 Single-union plates (and all-separate-plates) -> no comparison, no issue.
- [x] 3.5 Dependency-missing path -> single `check_skipped` warning, no raise (monkeypatch the import).
- [x] 3.6 Gate integration: a plan with a too-close co-plated pair does not report a clean pass and surfaces the issue in the fix prompt.

## 4. Verification

- [x] 4.1 `uv run pytest tests/test_plate_clearance_check.py` and the gate test file pass.
- [x] 4.2 `ruff check` / `ruff format` clean on the new and changed files; type-checkers (mypy, basedpyright) clean on `src/plate_clearance_check.py`.
- [x] 4.3 Update `CLAUDE.md`'s Core Scripts table and `quality_gate.py`'s description to mention the plate-clearance stage; remove the corresponding `TODO.md` line.
