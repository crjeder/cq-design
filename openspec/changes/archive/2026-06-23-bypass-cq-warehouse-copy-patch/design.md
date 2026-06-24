## Context

`cq_warehouse.extensions`, on import, rebinds class methods on
`cadquery.occ_impl.shapes.Shape`. Two of those rebindings are dangerous:

- `Shape.copy` -> a `copy.deepcopy(self, memo)` implementation.
- `Shape._apply_transform` -> calls `self.copy()` before applying the transform.

cadquery's deepcopy support is implemented via `__getstate__`/`__setstate__` using
`BinTools.Write_s`/`Read_s`. On OCCT 7.8 (`cadquery-ocp 7.8.1.1.post1`) the read side of
that round-trip aborts on certain point representations with
`BinTools_SurfaceSet::ReadGeometry: UnExpected BRep_PointRepresentation`. Native cadquery
`Shape.copy` does NOT use this path - it uses `BRepBuilderAPI_Copy(self.wrapped, ...)`,
which never serializes. So the crash exists only because `cq_warehouse` swaps the safe
implementation for the serialization-based one, globally, for the whole process.

The coexisting change `fix-orientation-bintools-deepcopy` fixes the *one* known hot path
(`placement.apply_cq`) by transforming `.wrapped` directly. This change removes the hazard
at its source: after `cq_warehouse.extensions` loads, restore the native copy/transform so
no code path - present or future - can be rerouted through `BinTools`.

## Goals / Non-Goals

**Goals:**
- Keep every useful `cq_warehouse.extensions` side effect (`Workplane.insertHole`, fastener
  geometry, etc.) working unchanged.
- Guarantee that, after the hardware blocks are imported, `Shape.copy` and
  `Shape._apply_transform` are cadquery's native, serialization-free implementations.
- Make the restore idempotent and safe to call from multiple import sites.

**Non-Goals:**
- Changing `placement.apply_cq` (owned by `fix-orientation-bintools-deepcopy`).
- Making the `cq_warehouse` import lazy (also owned by that change). This change is import-
  timing-agnostic: it neutralizes the patch wherever/whenever the import happens.
- Patching or vendoring `cq_warehouse` itself.

## Decisions

### Decision: snapshot native methods before import, restore after

A new module `src/cq_compat.py` exposes a single idempotent function, e.g.
`import_cq_warehouse_extensions()`, that:

1. Captures `Shape.copy` and (if present) `Shape._apply_transform` from
   `cadquery.occ_impl.shapes` **before** importing `cq_warehouse.extensions`.
2. Imports `cq_warehouse.extensions` (installing `Workplane.insertHole` etc.).
3. Rebinds the captured native `Shape.copy`/`Shape._apply_transform` back onto the class.

Snapshotting the live attribute and restoring it is version-safe: it reinstates exactly
the implementation shipped with the installed cadquery (2.7.0), with no need to
re-implement `BRepBuilderAPI_Copy` semantics or guess the `copy(self, mesh=...)` signature.

**Alternative considered - re-implement native copy.** Define our own
`copy = lambda self, mesh=False: self.__class__(BRepBuilderAPI_Copy(self.wrapped, True,
mesh).Shape())` and assign it after import. Rejected as the primary mechanism: it couples
this code to cadquery's exact copy signature/behavior and could drift from the installed
version. It is kept only as a fallback if the snapshot is somehow unavailable (see Risks).

**Idempotence.** The function records that the restore has run (module-level flag) and is a
no-op on subsequent calls, so importing it from several sites is harmless. If
`cq_warehouse.extensions` is already in `sys.modules` when first called (snapshot missed),
fall back to the re-implementation.

### Decision: route hardware.py through the shim

`src/blocks/hardware.py` replaces its module-top `import cq_warehouse.extensions` with a
call into `cq_compat`. This is the only place the skill imports the extensions for their
`Workplane` side effects, so it is the natural choke point. (If
`fix-orientation-bintools-deepcopy` later makes this import lazy inside `heat_set_boss`,
the lazy call site simply calls the same shim - the two changes compose.)

## Risks / Trade-offs

- **Snapshot taken too late (extensions already imported elsewhere first).** -> The shim
  detects `cq_warehouse.extensions in sys.modules` at first call and uses the
  `BRepBuilderAPI_Copy` re-implementation fallback to restore a safe copy, rather than
  reinstalling a patched one. The hardware blocks are the only importer in this codebase,
  so the snapshot path is the normal case.
- **cq_warehouse relies on its patched `_apply_transform` internally.** -> Its fastener
  construction does not depend on the deepcopy copy being active; fasteners are built then
  cast to plain `Solid`. The existing `tests/test_cq_warehouse_integration.py` exercises
  this and must continue to pass.
- **Overlap with `fix-orientation-bintools-deepcopy` on `hardware.py`.** -> Accepted
  (coexistence chosen). The edits touch the same import line; whichever lands second
  reconciles by calling the shim. No spec-file overlap: this change owns only the new
  `shape-transform-safety` capability.
