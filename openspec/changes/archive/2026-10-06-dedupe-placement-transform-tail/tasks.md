## 1. Refactor

- [x] 1.1 Add `_apply_trsf(workplane, trsf)` to `src/placement.py` containing the shared `BRepBuilderAPI_Transform` / `Shape.cast` / `newObject` tail and its explanatory comment
- [x] 1.2 Make `apply_cq` and `apply_matrix` build their `gp_Trsf` and return `_apply_trsf(...)`; trim duplicated docstring prose

## 2. Verification

- [x] 2.1 Add a test in `tests/test_placement.py` that `apply_matrix(wp, to_matrix(p))` and `apply_cq(wp, p)` yield the same geometry
- [x] 2.2 Run `uv run pytest tests/test_placement.py tests/test_model_export.py`
