## Why

`placement.apply_cq` and `placement.apply_matrix` (`src/placement.py`) differ only in how they build the OCCT `gp_Trsf`. Both then repeat the same tail: transform each shape's `.wrapped` via `BRepBuilderAPI_Transform` (kernel copy flag, bypassing the cq_warehouse-patched `Shape._apply_transform`/`copy`), `Shape.cast`, and `workplane.newObject`. The bypass rationale lives in two docstrings and must be kept in sync.

## What Changes

- Extract the shared tail into one private helper `_apply_trsf(workplane, trsf)` in `src/placement.py`.
- `apply_cq` and `apply_matrix` build their `gp_Trsf` and delegate to it.
- No public signature or behavior change.

## Capabilities

### New Capabilities

### Modified Capabilities
- `coordinate-frame`: adds a requirement that both placement appliers route through one kernel-level transform path (no `Shape.copy`/deepcopy round-trip).

## Impact

- `src/placement.py` only (bundled into `lib/` by `bundle_project.py`; no module-list change).
- Callers: `model_export._pose_union`. Tests: `tests/test_placement.py`, `tests/test_model_export.py`.
