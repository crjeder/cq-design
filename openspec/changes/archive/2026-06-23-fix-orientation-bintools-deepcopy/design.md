# Design

## Context

`cq_warehouse.extensions` (imported for `Workplane.insertHole`) replaces, on import:

- `Shape._apply_transform` -> `shape_apply_transform` (extensions.py:3529), which does
  `self.copy()` then `BRepBuilderAPI_Transform(...)`.
- `Shape.copy` -> `shape_copy` (extensions.py:3544), which does `copy.deepcopy(self, memo)`.

cadquery's `Shape.__getstate__`/`__setstate__` (shapes.py:1723/1732) implement the
pickle protocol with `BinTools.Write_s`/`Read_s`. `copy.deepcopy` of a `Shape` therefore
serializes `self.wrapped` to a BinTools stream and reads it back. The `memo` seeded with
`id(self.wrapped)` does not prevent this, because `__getstate__` serializes `wrapped`
directly rather than letting `deepcopy` walk it through the memo. The BinTools read side
raises `BRep_PointRepresentation = 153` on some surfaces (reproduced separately as
`Standard_OutOfRange: NCollection_IndexedMap::FindKey` on modeled-thread geometry; the
exact error is geometry-dependent and the round-trip is unreliable for complex faces).

Call chain that fails today:

```
apply_cq -> Workplane.rotate -> Shape.rotate -> Shape._apply_transform [PATCHED]
          -> self.copy() [PATCHED] -> copy.deepcopy -> __getstate__/__setstate__
          -> BinTools.Write_s (ok) + BinTools.Read_s (raises 153)
```

## Decision: Option A -- direct OCP transform in apply_cq

Apply the placement transform via the OCCT kernel directly, bypassing every patched
`Shape` method. One `gp_Trsf` is composed for the whole placement and applied to each
solid's `.wrapped` with `BRepBuilderAPI_Transform(wrapped, trsf, True)` (the `True` is
OCC's in-kernel copy flag -- a geometric copy, not a Python deepcopy, and not BinTools).

Sketch (final code lives in `src/placement.py`):

```python
def apply_cq(workplane, placement):
    if not placement:
        return workplane

    from math import radians
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from cadquery.occ_impl.shapes import Shape

    trsf = gp_Trsf()
    for step in placement.get("rotate", []):
        ax, ay, az = _AXIS_VEC[step["axis"]]
        r = gp_Trsf()
        r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(ax, ay, az)), radians(step["angle_deg"]))
        trsf = r * trsf                    # R_n * ... * R_1 (rotations in listed order)

    translate = placement.get("translate_mm")
    if translate:
        t = gp_Trsf()
        t.SetTranslation(gp_Vec(*translate))
        trsf = t * trsf                    # translate after rotations

    out = [Shape.cast(BRepBuilderAPI_Transform(v.wrapped, trsf, True).Shape())
           for v in workplane.vals()]
    return workplane.newObject(out)
```

### Why this matches existing semantics

`to_matrix` composes `translation @ R_n @ ... @ R_1` (rotations in listed order about
axes through the origin, then translation). `gp_Trsf` multiplication `a * b` applies `b`
then `a`, the same convention as matrix multiply, so building `trsf = R_i * trsf` in
listed order then `trsf = T * trsf` yields `T * R_n * ... * R_1` -- identical to
`to_matrix`. Identity placement still returns the workplane unchanged.

### Validation already performed

With `cq_warehouse.extensions` imported (patch active), transforming a modeled-thread
`HexNut` through this path with a tripwire on `Shape.copy` did not enter `Shape.copy`,
produced one solid, and exported a 299 KB STL. The previously failing path would have
deep-copied through BinTools.

## Decision: lazy cq_warehouse import in hardware.py

`src/blocks/hardware.py` imports `cq_warehouse.extensions` at module top only for
`insertHole`, used by exactly one function (`heat_set_boss`). The other three functions
(`socket_head_cap_screw`, `hex_head_screw`, `hex_nut`) use `Solid(screw.wrapped)` and do
not need the extension. Move `import cq_warehouse.extensions` into `heat_set_boss`.

Effect:
- Importing `blocks` runs `hardware.py`'s module body, which no longer imports
  `cq_warehouse`, so the global `Shape` patch is not installed and `cq_warehouse` is not
  loaded for hardware-free models.
- The patch is installed lazily the first time `heat_set_boss` runs. Even then,
  `apply_cq` is immune (option A), so placement/orientation export still works.

This is defense in depth: option A fixes the export regardless of the patch; lazy import
keeps the patch from ever being installed for the common (hardware-free) case.

## Alternatives considered

- **Restore `Shape._apply_transform`/`Shape.copy` after importing extensions.** Rejected:
  `insertHole` and other extension methods may rely on the patched `copy`; selectively
  un-patching is brittle and version-coupled to cq_warehouse internals.
- **Tessellate first, transform the trimesh.** Workable for the 3MF path but the per-union
  STL export still needs an oriented cq shape; option A is one chokepoint covering both.
- **`simple=True` threads only.** Narrows but does not eliminate the trigger -- `153` is a
  surface/point-representation read failure that is not guaranteed thread-specific.

## Risks

- `apply_cq` gains a dependency on `OCP.gp` / `OCP.BRepBuilderAPI` (already transitive via
  cadquery). Keep imports function-local so `to_matrix`'s lightweight trimesh-only path is
  unaffected.
- `Shape.cast` must yield the same wrapper types the rest of `model_export` expects
  (`Compound.makeCompound(workplane.vals())` downstream consumes `.vals()`); covered by
  existing export tests plus the new transform test.
