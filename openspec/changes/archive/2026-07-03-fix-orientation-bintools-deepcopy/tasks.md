## Implementation note

This change was satisfied by committed work (`7c9fe04 "Neutralize cq_warehouse's
unsafe Shape.copy monkeypatch"` plus the `placement.py` OCP transform) using a
**superset** of the proposed design: in addition to option A and the lazy import, a
`src/cq_compat.py` shim restores cadquery's native (serialization-free)
`Shape.copy`/`_apply_transform`/`located`/`moved` after loading `cq_warehouse.extensions`,
so even fastener *construction* stays off the BinTools round-trip. All tasks below are
marked against the code as it exists; boxes reflect the actual files.

## 1. Make apply_cq immune to the monkeypatch (option A)

- [x] 1.1 `src/placement.py` `apply_cq` composes the placement into one `gp_Trsf`
      (ordered X/Y/Z rotations about the origin, then translation) and applies it to each
      `workplane.vals()` entry via `BRepBuilderAPI_Transform(v.wrapped, trsf, True)` +
      `Shape.cast`, returning `workplane.newObject([...])`. Imports are function-local;
      identity placement returns the workplane unchanged. `apply_matrix` uses the same
      OCP path for derived mate-chain poses.
- [x] 1.2 Composition is `T * R_n * ... * R_1` (via `gp_Trsf.Multiplied`), matching
      `to_matrix`; covered by `tests/test_placement.py`.

## 2. Import cq_warehouse only when used

- [x] 2.1 `src/blocks/hardware.py` has no module-top `cq_warehouse` import; the extensions
      import is lazy inside `heat_set_boss` via `cq_compat.import_cq_warehouse_extensions()`.
      Fastener-class imports are function-local. `blocks/__init__.py` importing `hardware`
      no longer loads `cq_warehouse`.
- [x] 2.2 `hardware.py` module docstring documents the lazy, patch-neutralized import.
- [x] 2.3 (added) `src/cq_compat.py` imports the extensions for `Workplane.insertHole`
      and restores native `Shape` copy/transform methods, so the global monkeypatch is
      never left installed.

## 3. Tests

- [x] 3.1 `tests/test_placement.py` / `tests/test_cq_compat.py`: transforms applied with
      the extensions loaded do not go through the patched `Shape.copy` / a BinTools
      round-trip.
- [x] 3.2 `tests/test_hardware_lazy_import.py`: importing `blocks` does not import
      `cq_warehouse` and does not install the `Shape` patch.
- [x] 3.3 `tests/test_hardware_lazy_import.py`: `heat_set_boss` works via the lazy import
      and `Workplane.insertHole` is available.
- [x] 3.4 `tests/test_model_export.py`: `export_model` with a non-identity print
      orientation produces the 3MF and STLs without a BinTools error.

## 4. Verify

- [x] 4.1 `uv run pytest tests/` -> 302 passed.
- [x] 4.2 Real model regenerated: `py -3.12 build.py` in
      `D:/3D Druck/C5 Mobile Phone Holder/build` completes (exit 0), writing `plate.stl`
      in the X+90/Z+90 print orientation, `cradle.stl`, and `model.3mf`, with no
      `BinTools_ShapeSet::ReadGeometry` / `BRep_PointRepresentation` error.
- [x] 4.3 `openspec validate "fix-orientation-bintools-deepcopy" --strict` passes.
- [x] 4.4 `src/placement.py`, `src/blocks/hardware.py`, `src/cq_compat.py`, and the tests
      are committed (ruff-clean).
