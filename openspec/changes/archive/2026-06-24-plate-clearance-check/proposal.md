## Why

When two or more unions share a plate (print-in-place), they are printed in one job at
fixed relative positions. If any two of them come closer than one layer height anywhere,
the slicer bridges the gap and they **fuse into a single solid** in the print -- a working
joint locks up, or two parts meant to separate come out as one. The quality gate today has
no check for this: it validates overhang, watertightness, DFM, and kinematic range, but
never measures the gap between co-plated unions. A plan that places two unions 0.05 mm
apart on a 0.2 mm-layer print passes the gate clean and prints as a fused blob.

The fix is a geometric invariant that is cheap to verify: `model_export` fuses each plate
as a **rigid cluster** (`model_export.py:124-138`) -- the unions keep their assembled
relative transforms and the whole cluster is rotated together into print orientation. A
rigid rotation preserves distances, so the minimum surface-to-surface gap between two
co-plated unions is the same in print orientation as in the assembled pose. The gate can
therefore measure it on the **assembled-pose per-union STLs the kinematic check already
consumes**, with no new export and no print-orientation bookkeeping.

## What Changes

- **Add a plate-clearance stage to the quality gate.** For every plate that holds more
  than one union, the gate SHALL compute the minimum surface-to-surface distance between
  each pair of co-plated unions and flag any pair whose gap is at or below the plate's
  clearance threshold (one layer height). Single-union plates are skipped.
- **Measure on the assembled-pose union meshes.** The check SHALL reuse the assembled-pose
  per-union STLs already emitted for the kinematic check, relying on the rigid-cluster
  invariant so the assembled-pose gap equals the print-orientation gap. No new export
  artifact is introduced.
- **Derive the threshold from the print recipe's layer height.** The clearance threshold
  SHALL be one layer height, derived the same way the gate derives `layer_height_mm` for
  its print recipe (`nozzle_mm * 0.5`), so the check stays consistent with the recipe the
  gate already reports.
- **Report with the structured issue contract and block on failure.** Findings SHALL use
  the existing `{source, severity, type, message, hint}` contract with
  `type: "plate_clearance"` and `severity: "error"` (fusing is a hard print failure),
  naming the two unions, the plate, the measured gap, and the threshold. The check SHALL
  degrade to a single `check_skipped` warning when its geometry dependencies (trimesh and
  the collision/distance backend) are unavailable, matching the kinematic check.

## Capabilities

### New Capabilities
- `plate-clearance-validation`: the quality gate measures the minimum gap between every
  pair of unions that share a plate and reports an error when any gap is at or below one
  layer height, preventing co-plated unions from fusing in the print.

## Impact

- Tooling: new `src/plate_clearance_check.py` (the stage), wired into
  `quality_gate.run_gate` alongside `_run_kinematic_stage` (`quality_gate.py:299,424-425`).
  Reuses the assembled-pose union STLs from `model_export` and the trimesh/python-fcl
  stack already required by `kinematic_check.py`.
- Specs: new `plate-clearance-validation` capability. `overhang-analysis` and
  `kinematic-range-validation` are unaffected (this is an additional, independent stage).
- Tests: new `tests/test_plate_clearance_check.py` (two unions below / above threshold;
  single-union plate skipped; dependency-missing degrades to `check_skipped`).
- Out of scope: clearance against the bed or other plates, support-interface gaps, and
  any per-pair clearance override in the plan (the threshold is one layer height).
