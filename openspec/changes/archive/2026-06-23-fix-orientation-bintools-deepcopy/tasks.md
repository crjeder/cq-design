## 1. Make apply_cq immune to the monkeypatch (option A)

- [x] 1.1 In `src/placement.py`, rewrite `apply_cq` to compose the placement into one
      `gp_Trsf` (ordered X/Y/Z rotations about the origin via `SetRotation`, then
      `SetTranslation`) and apply it to each `workplane.vals()` entry via
      `BRepBuilderAPI_Transform(v.wrapped, trsf, True)`, re-wrapping with `Shape.cast`
      and returning `workplane.newObject([...])`. Keep the `OCP`/`Shape` imports
      function-local. Identity placement still returns the workplane unchanged.
- [x] 1.2 Confirm the composed transform matches `to_matrix` (`T * R_n * ... * R_1`):
      rotation order is the listed order, translation is applied after rotations.

## 2. Lazy cq_warehouse import in hardware.py

- [x] 2.1 In `src/blocks/hardware.py`, remove the module-top
      `import cq_warehouse.extensions` and the `import` of `Solid`/`cq` only if unused;
      move `import cq_warehouse.extensions` into `heat_set_boss` (the only function that
      calls `.insertHole`). Leave the existing function-local fastener-class imports.
- [x] 2.2 Update the `hardware.py` module docstring to state the extensions import is
      lazy (installed only when `heat_set_boss` runs), not at import time.

## 3. Tests

- [x] 3.1 Add a test: with `cq_warehouse.extensions` imported (patch active), `apply_cq`
      applied to a workplane transforms its geometry without entering the patched
      `Shape.copy` (assert via a `Shape.copy` tripwire or by asserting no exception on a
      shape whose BinTools round-trip would fail), and the result exports to a valid STL.
- [x] 3.2 Add a test: importing `blocks` (or `blocks.primitives`) does not import
      `cq_warehouse` (`assert "cq_warehouse" not in sys.modules`) and does not replace
      `Shape._apply_transform` with the patched version.
- [x] 3.3 Add a test: calling `heat_set_boss(...)` works and (after the call) the
      extension is loaded, confirming the lazy path still enables `insertHole`.
- [x] 3.4 Add/verify a regression test that `model_export.export_model` with a non-trivial
      `placement` (rotation present) on a block-importing part produces the 3MF and STLs
      without a BinTools error.

## 4. Verify

- [x] 4.1 Run `uv run pytest tests/` and confirm the new and existing tests pass.
- [x] 4.2 Regenerate the failing real model via `build.py` (or an equivalent multi-part
      plan with a non-identity print orientation) and confirm it completes with no
      `BinTools_ShapeSet::ReadGeometry` / `BRep_PointRepresentation` error.
- [x] 4.3 Run `openspec validate "fix-orientation-bintools-deepcopy" --strict`.
- [x] 4.4 Run `ruff check --fix` and `ruff format` on `src/placement.py`,
      `src/blocks/hardware.py`, and the new tests.
