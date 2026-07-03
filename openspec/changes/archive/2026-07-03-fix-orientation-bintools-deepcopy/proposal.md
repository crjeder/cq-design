## Why

`build.py` (and the skill's print-orientation export) fails on real models with:

```
build failed: EXCEPTION in BinTools_ShapeSet::ReadGeometry(S,OS)
Standard_Failure: BinTools_SurfaceSet::ReadGeometry: UnExpected BRep_PointRepresentation = 153
```

Root cause (traced and reproduced): `cq_warehouse.extensions`, imported at module top
of `src/blocks/hardware.py` for its `Workplane.insertHole` side effect, also
monkeypatches `Shape._apply_transform` and `Shape.copy` globally. The patched
`_apply_transform` calls `self.copy()` first, and the patched `Shape.copy` runs
`copy.deepcopy(self)`, which routes through cadquery's `Shape.__getstate__`/
`__setstate__` -> `BinTools.Write_s`/`Read_s`. The read side of that BinTools round-trip
cannot parse the point representation of some surfaces (OCCT 7.8) and raises
`BRep_PointRepresentation = 153`.

Consequences:
- Once any part script does `from blocks import ...` (even for a plain `fillet_box`),
  the old `blocks/__init__` eagerly imports `blocks.hardware`, installing the patch for
  the whole process. Every `placement`/print-orientation transform in `model_export.py`
  (via `placement.apply_cq` -> `Workplane.rotate`/`translate`) then deep-copies the shape
  through BinTools. The first transform applied is the first to hit the failing read.
- Assembled-pose export escapes only when parts have identity `placement` (no transform
  is ever applied); the print-orientation step is the first real rotation, so it is where
  the failure surfaces -- making it look like "rotation breaks the geometry" when the
  transform path is being silently rerouted through a fragile serialization round-trip.
- Models that use no hardware block still pay the cost, because importing `blocks`
  installs the global patch.

Verified: a transform applied directly via `OCP.BRepBuilderAPI.BRepBuilderAPI_Transform`
on the shape's `.wrapped` (bypassing the patched `Shape.copy`/`_apply_transform`)
transforms the geometry and exports a valid STL without ever entering `Shape.copy`.

## What Changes

- **Make `placement.apply_cq` immune to the monkeypatch (option A).** Compose the
  placement (ordered X/Y/Z rotations through the origin, then translation) into a single
  `gp_Trsf` and apply it to each value's `.wrapped` via `BRepBuilderAPI_Transform(...,
  copy=True)`, re-wrapping with `Shape.cast`. This never calls the patched
  `Shape.rotate`/`translate`/`copy`, so no `copy.deepcopy` and no BinTools round-trip
  occur, regardless of whether `cq_warehouse.extensions` is loaded. Behavior (rotation
  order, translation-after-rotation, identity when absent) is unchanged and stays
  consistent with `placement.to_matrix`.
- **Import `cq_warehouse` only when actually used.** Remove the module-top
  `import cq_warehouse.extensions` from `src/blocks/hardware.py` and load it lazily inside
  the single function that needs `insertHole` (`heat_set_boss`). After this, importing
  `blocks` does not import `cq_warehouse` and does not install the global Shape patch; the
  patch is handled lazily only when a hardware function that requires it runs.

## Capabilities

### Modified Capabilities
- `model-export`: placement and print-orientation transforms must be applied without
  deep-copying / serializing the shape, so they cannot trigger the cq_warehouse-induced
  BinTools round-trip.
- `block-library`: hardware blocks import `cq_warehouse` lazily (only when used), so
  importing the block package does not install the global `Shape` monkeypatch.

## Impact

- Code: `src/placement.py` (`apply_cq`/`apply_matrix` via direct OCP transform),
  `src/blocks/hardware.py` (lazy import), `src/cq_compat.py` (patch-neutralizing shim).
- Tests: `tests/test_placement.py`, `tests/test_cq_compat.py`,
  `tests/test_hardware_lazy_import.py`, `tests/test_model_export.py`.
- No schema, prompt, or plan-format changes. No change to the `placement` convention or
  to `to_matrix`.
