## Why

`cq_warehouse.extensions` (imported for `Workplane.insertHole`) globally monkeypatches
`Shape.copy` to run `copy.deepcopy`, which routes through cadquery's
`__getstate__`/`__setstate__` -> `BinTools.Write_s`/`Read_s`. On OCCT 7.8 the read side of
that round-trip rejects some surfaces' point representations and aborts the whole process
with `BinTools_SurfaceSet::ReadGeometry: UnExpected BRep_PointRepresentation`. Because the
patch is global, the failure is not confined to `placement.apply_cq` - it can surface in
*any* code path that copies or transforms a shape once `cq_warehouse` has been imported.

## What Changes

- **Neutralize the unsafe copy patch process-wide.** Add a small compatibility shim that
  imports `cq_warehouse.extensions` for its legitimate `Workplane` side effects (e.g.
  `insertHole`) and then restores cadquery's native, serialization-free `Shape.copy`
  (`BRepBuilderAPI_Copy`-based) and `Shape._apply_transform`. After this, no shape copy or
  transform anywhere in the process goes through the `deepcopy`/`BinTools` round-trip,
  regardless of which code triggered the `cq_warehouse` import.
- **Route the `hardware.py` extensions import through the shim** so that loading the
  hardware blocks installs the useful `Workplane` methods but leaves the safe copy in
  place.
- This is the global root fix and is complementary to the localized `apply_cq` rewrite in
  `fix-orientation-bintools-deepcopy`: even if a future transform path forgets to bypass
  the patch, the patch itself is no longer dangerous.

## Capabilities

### New Capabilities
- `shape-transform-safety`: the skill's Python environment guarantees that importing
  `cq_warehouse` does not leave the global `Shape.copy`/`_apply_transform` replaced with a
  serialization-based implementation; shape copies and transforms use cadquery's native
  `BRepBuilderAPI_Copy` path and never perform a `BinTools` round-trip.

### Modified Capabilities
<!-- None. The localized model-export / block-library requirement deltas are owned by the
     coexisting fix-orientation-bintools-deepcopy change; this change adds an independent
     safety capability and does not alter their requirements. -->

## Impact

- Code: new `src/cq_compat.py` (extensions-import shim + native-copy restore);
  `src/blocks/hardware.py` (import `cq_warehouse.extensions` via the shim instead of
  directly).
- Tests: assert that after importing the hardware blocks, `Shape.copy` is cadquery's
  native implementation (not the deepcopy patch) and that transforming/copying a shape
  whose `BinTools` round-trip would fail still succeeds and exports a valid STL.
- Dependencies: no version changes. `Workplane.insertHole` and the fastener classes remain
  available exactly as before.
- No schema, prompt, plan-format, or `placement`-convention changes.
