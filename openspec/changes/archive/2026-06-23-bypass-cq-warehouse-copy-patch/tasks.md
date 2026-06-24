## 1. Compatibility shim

- [x] 1.1 Add `src/cq_compat.py` with an idempotent
      `import_cq_warehouse_extensions()` that: (a) snapshots `Shape.copy`,
      `_apply_transform`, `located`, `moved`; (b) imports `cq_warehouse.extensions`;
      (c) rebinds the snapshotted native methods back onto `Shape`. Guarded by a
      module-level `_restored` flag so repeat calls are no-ops.
- [x] 1.2 Handle the late-call case: if `cq_warehouse.extensions` is already in
      `sys.modules` on first call, restore safe `Shape.copy`/`_apply_transform` via a
      `BRepBuilderAPI_Copy`/`BRepBuilderAPI_Transform` re-implementation instead of
      reinstating the patch. `OCP` imports are function-local.
- [x] 1.3 Confirmed against installed cadquery 2.7.0: `Shape` has native `copy`,
      `_apply_transform`, `located`, `moved`; `cq_warehouse.extensions` overwrites exactly
      those four. The deepcopy crash is because cadquery 2.7.0 added
      `__getstate__`/`__setstate__`, so `copy.deepcopy` serializes via `BinTools` and the
      memo seeded in cq_warehouse's `shape_copy` is never consulted. Restoring the four
      native methods makes `rotate`/`translate` (and `located`/`moved`) safe.

## 2. Route hardware.py through the shim

- [x] 2.1 In `src/blocks/hardware.py`, route the `cq_warehouse.extensions` import through
      `cq_compat.import_cq_warehouse_extensions()` (preserving `insertHole`). NOTE: the
      coexisting `fix-orientation-bintools-deepcopy` change had already made this import
      lazy (inside `heat_set_boss`); reconciled by routing that lazy import through the
      shim. Module docstring updated to note native `Shape.copy` is restored.

## 3. Tests

- [x] 3.1 `tests/test_cq_compat.py::test_shim_restores_native_copy_and_keeps_insert_hole`:
      after the shim runs, `Workplane.insertHole` exists AND `Shape.copy` /
      `_apply_transform` are native (`__module__ == "cadquery.occ_impl.shapes"`).
- [x] 3.2 `test_copy_and_transform_do_not_deepcopy` (tripwire on `__setstate__` proves the
      deepcopy/BinTools path is not used) and `test_transformed_shape_exports_valid_stl`
      (rotated solid exports to a watertight STL).
- [x] 3.3 `test_shim_is_idempotent`: second call is a no-op; `Shape.copy` stays native.
- [x] 3.4 `tests/test_cq_warehouse_integration.py` passes (3/3); added
      `test_heat_set_boss_uses_insert_hole` covering the lazy hardware path.

## 4. Verify

- [x] 4.1 `uv run pytest tests/`: new (5) + integration (3) pass. NOTE: 5 pre-existing
      failures in `test_kinematic_check.py` (plan_validate dof checks) are unrelated to
      this change - `src/plan_validate.py` was already modified in the working tree at
      session start; those tests touch neither `cq_compat.py` nor `hardware.py`.
- [ ] 4.2 Not runnable in this checkout: no `build/` model is committed (the failing
      `build/plate.py` from `occ-error.md` was generated during a skill run). Equivalent
      proof provided by the tripwire + rotated-STL export tests in 3.2. Re-run against a
      real generated model when one is available.
- [x] 4.3 `openspec validate "bypass-cq-warehouse-copy-patch" --strict` -> valid.
- [x] 4.4 `ruff check --fix` and `ruff format` on `src/cq_compat.py`,
      `src/blocks/hardware.py`, `tests/test_cq_compat.py` -> all checks passed.
