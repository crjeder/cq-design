## Context

Both appliers import `Shape`, `BRepBuilderAPI_Transform`, build a `gp_Trsf`, and run an identical list comprehension plus `newObject`. See `src/placement.py`.

## Goals / Non-Goals

**Goals:**
- One implementation of the kernel transform tail and one place documenting why `Workplane.rotate`/`translate` is avoided.

**Non-Goals:**
- Changing the `placement` convention, `to_matrix`, or the `apply_cq`/`apply_matrix` signatures.
- Merging the two appliers into one function; their `gp_Trsf` construction legitimately differs.

## Decisions

- Private `_apply_trsf(workplane, trsf)` holding the lazy OCP/cadquery imports and the transform. Alternative: have `apply_cq` build a matrix via `to_matrix` and call `apply_matrix`; rejected because it reroutes the primary path through numpy and `SetValues`, a behavior change for no gain.

## Risks / Trade-offs

- Behavior drift in the primary pose path -> existing `test_placement.py` convention and no-deepcopy tests, plus `test_model_export.py`, cover it.
