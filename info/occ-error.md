# OCC deepcopy crash on print-orientation rotation of `plate.py`

Status: worked around, root cause not fixed. This documents the bug for later investigation.

## Symptom

Exporting `build/plate.py` in print orientation fails inside `model_export.py` when it
rotates the plate's B-rep solid (cover face down = `rotate X+90` then `Z+90`). Two error
signatures seen, depending on geometry/run:

```
OCP.OCP.Standard.Standard_Failure:
  EXCEPTION in BinTools_ShapeSet::ReadGeometry(S,OS)
  Standard_Failure: BinTools_SurfaceSet::ReadGeometry: UnExpected BRep_PointRepresentation = 42

OCP.OCP.Standard.Standard_OutOfRange: NCollection_IndexedMap::FindKey
```

It is partly **flaky**: the same shape sometimes rotates once in isolation but fails
inside `model_export` (which does two chained rotations + 3MF assembly), and some
geometry variants fail deterministically.

## Where it comes from

`model_export.py` -> `placement.apply_cq()` -> `cadquery.Workplane.rotate()`
-> `Shape._apply_transform()` -> **cq_warehouse** monkeypatched
`Shape.copy()` (`cq_warehouse/extensions.py:3540`) -> `copy.deepcopy(shape)`
-> `Shape.__setstate__` (`cadquery/occ_impl/shapes.py:1736`) -> `BinTools.Read_s(...)`.

cq_warehouse's `shape_copy` serializes the OCC shape to a binary buffer with `BinTools`
and reads it back. The **read** step rejects a point/surface representation the **write**
step emitted -> the crash. So it is a `BinTools` round-trip serialization bug surfaced by
cq_warehouse's deepcopy-based copy, triggered by particular plate edges.

Full traceback tail:
```
  File ".../cq_warehouse/extensions.py", line 3523, in shape_apply_transform
    shape_copy = self.copy()
  File ".../cq_warehouse/extensions.py", line 3540, in shape_copy
    copy_of_shape = copy.deepcopy(self, memo)
  File ".../copy.py", line 261, in _reconstruct
    y.__setstate__(state)
  File ".../cadquery/occ_impl/shapes.py", line 1736, in __setstate__
    BinTools.Read_s(wrapped, data[0])
```

## Environment

- cadquery 2.7.0
- cq_warehouse 0.8.0
- cadquery-ocp 7.8.1.1.post1 (OCCT 7.8)
- numpy 2.4.6, trimesh 4.12.2
- Python 3.12, Windows 11
- venv: `C:/Users/puck-/.claude/skills/cq-design/.venv`

## What is and isn't affected

- `cradle.py` rotates fine through the identical path (fillets + axle bores). Only the
  **plate** triggers it.
- The plate **validates and renders fine** (`run_cadquery_model.py`: watertight, manifold,
  no thin walls) and **exports STL fine** via `cq.exporters.export` — STL export does not
  use the cq_warehouse deepcopy path. Only `.rotate()` (deepcopy) trips it.

## Bisected triggers (plate-specific geometry)

1. **Single axle bore spanning the open clevis slot.** The original
   `_x_cyl(gx0 - EAR_T - 0.1, gap_w + 2*EAR_T + 0.2, PLATE_PIN_R)` cut one cylinder through
   ear -> open gap -> ear. Boring **each ear separately** (two short cylinders, identical
   resulting solid) removes one trigger.
2. **Pure-45-deg snap-pocket ceiling (no flat cap).** A 4-point pocket profile whose 45-deg
   ramp meets the back wall at the apex (0 mm^2 overhang) crashes the rotation
   deterministically. Keeping a 5-point profile with a ~1.2 mm horizontal cap at the deep
   back rotates/exports reliably.

Both fixes are currently in `build/plate.py` with explanatory comments.

## Reproduction (minimal)

```python
import sys; sys.path.insert(0, r"C:/Users/puck-/.claude/skills/cq-design/src")
import cadquery as cq
from exporters import _load_result
r = _load_result("build/plate.py")
r.rotate((0,0,0), (1,0,0), 90).val()   # may raise; chain a 2nd rotate to make it reliable
```

`model_export.py --orientations build/orientations.json` is the real-world repro (does
X+90 then Z+90). Run it several times — failures are intermittent on borderline geometry,
deterministic on the pure-45 pocket.

## Workarounds that did NOT help

- `.clean()` on the result.
- BREP round-trip (`exportBrep` / `importBrep`).
- STEP round-trip (`exportStep` / `importStep`).

All still fail because the crash is in the deepcopy read, regardless of how the shape was
rebuilt.

## Leads to investigate later

- `BRep_PointRepresentation = 42` is an unknown/unhandled subtype code in
  `BinTools_SurfaceSet::ReadGeometry`. Likely a write/read version mismatch or an edge
  carrying a `BRep_PointOnCurveOnSurface` / `BRep_PointOnSurface` representation that the
  reader doesn't expect. Inspect the offending edges' point representations on the plate
  (the per-ear bore circles intersecting pocket/slot faces).
- Try `BinTools` ascii vs binary, or a newer/older cadquery-ocp (OCCT) build, to see if the
  round-trip stabilizes.
- Consider replacing cq_warehouse's deepcopy-based `Shape.copy` with `BRepBuilderAPI_Copy`
  (`shape.copy()` via OCC's native copier) which avoids serialization entirely. If patched
  in cq_warehouse/cadquery, the pure-45 pocket + spanning bore would likely both work.
- Alternatively, make `model_export` rotate the **mesh** (trimesh) for the print-oriented
  3MF objects instead of the B-rep, sidestepping the deepcopy path. The kinematic-check
  STLs are already mesh-based.

## Verification that the workaround holds

`model_export.py` ran 4/4 successfully with the shipped geometry. Print-orientation
overhang (own measurement, faces >44 deg downward, elevated above bed):
plate 37 mm^2 (pocket caps + horizontal pin bores), cradle 17 mm^2.
