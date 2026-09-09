# CadQuery Pattern Reference

## CadQuery Workplane Naming (XY/XZ/YZ)

`cq.Workplane("XY")`, `"XZ"`, `"YZ"` name the sketch plane, not a world-frame
convention (that's `prompts/planning.md`'s separate North/East/Up vocabulary for
assembly placement) -- which two local axes a 2D sketch spans before
`.extrude()`/`.revolve()` lifts it into 3D:

- `"XY"` -- sketch spans X/Y, extrudes along Z (Z is up); normal = +Z
- `"XZ"` -- sketch spans X/Z, extrudes along Y (Y is depth); normal = **-Y**, so an
  uncentered extrude or `.box()` third dimension grows into **negative** Y, not positive
  (verify with a bbox probe before porting Y coordinates from an `"XY"`-authored body)
- `"YZ"` -- sketch spans Y/Z, extrudes along X (X is width); normal = +X

Millimeters throughout. A workplane is a local 2D coordinate system: an **origin**
(local (0,0) in 3D), an **x-direction**, and a **normal** (local Z). Sketch ops are
defined in that local frame, then lifted into 3D.

```python
cq.Workplane("XY")                                            # named plane, origin (0,0,0)
cq.Workplane(cq.Plane(origin=(0, 0, 10), normal=(0, 0, 1)))    # explicit origin + normal
solid.faces(">Z").workplane()                                  # on a face (origin per centerOption)
solid.faces(">Z").workplane(offset=5)                          # offset along face normal
# .transformed() moves the CURRENT plane; cumulative, local X,Y,Z rotation order
solid.faces(">Z").workplane().transformed(offset=(5, 5, 0), rotate=(0, 0, 45))
```

Basic shapes (`.box(w,d,h)`, `.cylinder(h,r)`, `.sphere(r)`, `.polygon(n,d)`,
`.ellipse(rx,ry)`) are recallable; the non-obvious signature is
`.wedge(dx,dy,dz,xmin,zmin,xmax,zmax)`.

## Face & Edge Selectors

### Basic Selectors

```python
# Face (by normal vector): >Z/<Z/>X/<X/>Y/<Y max/min position; +Z/-Z normal direction;
# |Z parallel to axis; #Z perpendicular to axis; %Plane/%Cylinder/%Cone/%Sphere/%Torus by type
.faces(">Z")          # top face (max Z centroid)
.faces("%Cylinder")   # cylindrical faces only

# Edge (by direction): |Z/|X/|Y parallel; #Z perpendicular; >Z/<Z max/min position;
# %Circle/%Line by curve type
.edges("|Z")          # vertical edges
.edges("%Circle")     # circular edges only

# Vertex (by position): .vertices(">Z") / .vertices("<X")
```

### Selector Modifier Reference

| Modifier | Meaning | On faces | On edges |
|---|---|---|---|
| `>` / `<` | Max / min | Face at max/min position | Edge at max/min position |
| `+` / `-` | Direction | Normal in +/- direction | Edge aligned +/- direction |
| `|` | Parallel | Normal parallel to axis | Edge parallel to axis |
| `#` | Perpendicular | Normal perpendicular to axis | Edge perpendicular to axis |
| `%` | Type | `%Plane`,`%Cylinder`,`%Cone`,`%Sphere`,`%Torus` | `%Circle`, `%Line` |

### Nth Selector & Compound Selectors

```python
# --- Nth selector (sort by centroid along an axis, pick by 0-based index) ---
.edges(">Z[0]")    # max Z (same as ">Z")          .edges(">Z[1]")   # 2nd highest Z
.faces("<Y[-1]")   # last face from min-Y end       .edges("<<X[0]")  # lowest X centroid
.faces(">>Z[1]")   # explicit sorted-index: >> sorts high->low, << low->high

# --- Custom direction vector ---
.edges(">(-1, 1, 0)")             # edge max in (-1,1,0) direction
.chamfer(1).edges("+(-1, 1, 0)")  # chamfer in specific direction

# --- Logical combinations ---
.edges("|Z and >X")   # parallel to Z AND max X    .edges("|Z or |X")  # parallel to Z OR X
.faces("not >Z")      # all faces except top        .edges("|Z exc >X") # parallel to Z, excluding max X

# --- Compound selectors ---
.faces(">Z").edges()          # all edges of top face
.faces(">Z").edges("|X")      # X-direction edges of top face
```

### Programmatic Selection

```python
result.faces().filter(lambda f: f.Area() > 100)   # filter with a lambda
result.edges().sort(lambda e: e.Length())[:3]      # sort + slice: 3 shortest edges
result.faces(">Z").ancestors("SOLID")               # solid containing the top face
result.edges(">Z").siblings("%Circle")              # sibling circular edges
```

### Selector Semantics (read before trusting a selection)

- **`>Z` tests the centroid, not the highest point.** On a slanted or irregular
  solid the max-centroid face/edge is not necessarily the one containing the
  topmost vertex.
- **`|axis` (parallel) vs `+/-axis` (direction).** `|Z` selects every face whose
  normal is parallel to Z -- on a box, BOTH top and bottom. `+Z`/`-Z` narrow to the
  single face pointing that way; use `>Z` for "the top face" specifically.
- **`#axis` (orthogonal).** `#Z` selects faces orthogonal to Z (box sides) and
  edges orthogonal to Z (horizontal edges).
- **Prefer chaining over a combined string.** `.faces(">Z").edges("%Circle")` is
  more predictable than `.edges("%Circle and >Z")`.

### Tags (stable selection)

Tags are the most stable selection mechanism -- they survive feature additions
that shift index-based selectors. Tag a face/edge as soon as it is created:

```python
result = (
    cq.Workplane("XY").box(20, 20, 10)
    .faces(">Z").tag("top").end()
    .faces("<Z").tag("bottom").end()
    .faces(tag="top").workplane().hole(4)      # survives fillets/features added in between
    .faces(tag="bottom").workplane().hole(2)
)
```

Tags are stored on the Workplane, not the shape; `.end()` returns to the solid
context after tagging (`reference/CadQuery Anti-Patterns.md`, Tier 2).

## 2D Construction / Sketch API

```python
# Closed wires: .rect(xLen,yLen) .circle(r) .ellipse(rx,ry) .polygon(nSides,diameter)
# Pen: .moveTo(x,y) .lineTo(x,y) .line(dx,dy) .hLine(d) .vLine(d) .polarLine(d,angle)
# Curves: .threePointArc((x2,y2),(x3,y3)) .sagittaArc(end,sag) .radiusArc(end,r)
#         .tangentArcPoint((x,y)) .spline([(x1,y1),...]); .close() closes to start.
# sagittaArc: positive sag bows LEFT of travel direction (left->right = bows upward/convex);
# sag = R - sqrt(R^2 - (chord/2)^2)

# Sketch object: .rect/.circle/.ellipse/.trapezoid/.regularPolygon/.polygon, mode="a" add
# (default)/"s" subtract/"i" intersect, .push([...]) replicates the next op per point,
# .finalize() required before returning to Workplane ops.
result = (cq.Workplane("XY").sketch().rect(20, 20).circle(5, mode="s")
          .push([(0, 0), (20, 0)]).circle(3).finalize().extrude(10))

# Reusable profile with .placeSketch() -- define once, place at many locations
slot = cq.Sketch().slot(8, 3)          # length, width
result = (cq.Workplane("XY").box(40, 20, 8).faces(">Z").workplane()
          .placeSketch(slot.moved(cq.Location((-10,0,0))), slot.moved(cq.Location((10,0,0))))
          .cutBlind(-4))
```

## Machining Operations (Holes, Shell, Fillet)

```python
.edges("|Z").fillet(radius)            # vertical edges; .edges().fillet(r) = all
.edges("|Z").chamfer(distance)         # or .chamfer(len, len2) asymmetric
.faces(">Z").hole(diameter)            # through hole    .faces(">Z").hole(diameter, depth)  # blind
.faces(">Z").cboreHole(hole_d, cbore_d, cbore_depth)        # counterbore
.faces(">Z").cskHole(hole_d, csk_d, csk_angle)              # countersink
.cutBlind(depth)  / .cutBlind(depth, taper=angle)           # cut current wire to depth (tapered)
.cutThruAll()     / .cutThruAll(taper=angle)                # cut through all (tapered)
# cuts along the workplane normal (points OUTWARD from a selected face) -- invert=True to cut IN
.faces(">Z").workplane(invert=True).rect(5, 5).cutBlind(3)
.faces(">Z").shell(-wall_thickness)    # hollow, top open   .shell(-wall_thickness)  # auto-open thinnest
.faces(">Z").workplane().pushPoints([(x1,y1), (x2,y2)]).hole(d)         # positioned holes
.faces(">Z").workplane().pushPoints([(x1,y1)]).circle(r).extrude(h)     # positioned bosses
.faces(">Z").workplane().text("TEXT", fontsize, depth)      # depth>0 embossed, depth<0 engraved
```

## Advanced 3D Operations (Loft, Sweep, Revolve)

```python
# Loft (ruled=True for straight loft): cross-sections connected smoothly
result = cq.Workplane("XY").rect(10, 10).workplane(offset=10).circle(5).loft()
# Sweep: extrude a profile along a path
path = cq.Workplane("XZ").spline([(0,0), (10,10), (20,0)])
result = cq.Workplane("XY").circle(1).sweep(path)
# revolve(angleDegrees, axisStart, axisEnd) -- note the argument order
result = (cq.Workplane("XY").moveTo(10,0).lineTo(10,10).lineTo(15,10).lineTo(15,0)
          .close().revolve(360, (0, 0, 0), (0, 1, 0)))   # 360 deg around Y axis
# twistExtrude(height, twistAngleDegrees)
result = cq.Workplane("XY").polygon(6, 10).twistExtrude(20, 90)
```

`rarray(xc,yc,xs,ys)` / `polarArray(r,start,angle,count)` cover rectangular and
polar arrays.

## Transform & Boolean Operations

```python
# .translate() applies to a built Shape/finished result, moving it in the GLOBAL frame --
# not a mid-chain positioning primitive (CadQuery Anti-Patterns.md, Tier 2). Use
# .center()/.moveTo() or a fresh workplane to position while building.
result = part.translate((dx, dy, dz))
result = part.rotate(axisStartPoint=(0,0,0), axisEndPoint=(0,0,1), angleDegrees=45)
result = part.rotateAboutCenter(axisEndPoint=(0, 0, 1), angleDegrees=45)
result = part.mirror("XY")   # or "YZ" / "XZ"
result = part.split()        # split at current workplane

result = part_a.union(part_b)      # union
result = part_a.cut(part_b)        # difference
result = part_a.intersect(part_b)  # intersection
result = wp.combine()              # union everything on the stack
```

## Non-Overlapping Part Assembly (Performance)

For plates/arrays where parts don't touch, skip `.union()` (O(n^2) OCCT booleans)
and combine into one compound instead -- 5-10x faster than unioning for 20+ parts:

```python
from cadquery import Compound
parts = [gauge1, gauge2, ...]
compound = Compound.makeCompound([p.val() for p in parts])
cq.exporters.export(compound, "plate.stl")
```

`makeCompound()` works directly on CQ Workplane `.val()` objects; for raw OCC
solids build a `TopoDS_Compound` via `BRep_Builder` instead.

## Center Selection

`centerOption` controls where `.workplane()` puts the origin on a selected face:

| Value | Origin location |
|---|---|
| `"CenterOfMass"` | Center of mass of the face |
| `"CenterOfBoundBox"` | Center of the face's bounding box |
| `"ProjectedOrigin"` | Parent workplane's origin projected onto the new plane (**default**) |

Never assume the default matches your intent -- on an irregular face
`ProjectedOrigin` can land far from where you expect (see
`reference/CadQuery Anti-Patterns.md`, Tier 2, origin drift).

## Common Gotchas

1. **Outer edge fillets before shell, small/detail fillets after** -- pre-existing
   small fillets can cause shell to fail.
2. **Fillet radius must be < the shortest edge it touches.**
3. **Boolean cuts must fully intersect** -- add 0.01mm extra depth.
4. **`.center()` is cumulative** -- each call offsets from the CURRENT center, not origin.
5. **`forConstruction=True`** for reference geometry that stays non-solid.
6. **`.workplane(offset=10)`** -- new workplane 10mm above the current one.
7. **Workplane origin stacking** -- `.center(x, y)` permanently mutates the plane
   origin; a later `.faces().workplane()` inherits it via `ProjectedOrigin` (the
   default), offsetting later features. See Workplane Context Stacking below.
8. **`combine='cut'` text deboss fails silently** -- use a fresh workplane +
   explicit `.cut()` instead. See `reference/emboss_text.md`.
9. **Additive text overflows body** -- `.text(..., combine='a')` can create
   geometry outside the body outline; clip with `.intersect()` or deboss instead.
10. **Prefer boolean subtraction over `.shell()` for enclosures** -- a separate
    cavity solid `.cut()` in is more robust than `.shell(-t)`, which frequently
    fails on filleted bodies or opens the wrong face. Reserve `.shell()` for
    simple uniform-wall cases. Order: outer shape -> exterior fillets -> cut
    cavity -> holes/cutouts. Not in tension with "prefer feature ops over
    booleans" (`CadQuery Anti-Patterns.md`, Tier 1): feature ops for
    bosses/holes/edges, booleans for separate solids AND cavities where
    `.shell()` is fragile.
11. **Revolved profiles on non-XY workplanes** -- `.transformed(offset=(a,b,c))`
    on XZ/YZ workplanes maps offset to the LOCAL frame, not world coordinates. On
    XZ, local-Y is world-Z and the normal is world **-Y**, so the third component
    flips sign: `offset=(cx, top_z, cy)` on XZ ends up at world `(cx, -cy, top_z)`.
    For revolved chamfer/fillet tools,
    prefer building on XY and translating the result, or verify with
    `verify_boolean` that the cut actually changed the geometry.
12. **A feature unioned in AFTER a cavity cut can poke through the cavity
    floor/wall into the hollow interior** -- a full-height boss/tab/dovetail
    unioned onto a body with an existing pit/pocket/shell cavity is only safe
    where its XY footprint sits *outside* the cavity's footprint; where it
    overlaps, the feature pokes into open space -- invisible from every exterior
    view (still flush with the outer wall), visible only in a section that
    crosses it. Clip the feature's height/extent to the actual solid thickness at
    that XY position (e.g. a seam tab under a pit: extrude only bed-to-cavity-floor,
    not full part height). Visual self-review must check this against a section
    crossing the feature (`reference/Visual Review Checklist.md`) -- exterior
    renders look identical either way.

## Workplane Context Stacking (Origin Drift)

`.center(x, y)` calls `plane.setOrigin2d()`, which **permanently mutates** the
workplane origin. A later `.faces(">Z").workplane()` with the default
`centerOption="ProjectedOrigin"` projects the *current* (shifted) origin onto the
new face -- NOT the face center.

```python
# Bug: text lands 10mm off-center
result = (
    cq.Workplane("XY").box(40, 40, 10)
    .faces(">Z").workplane()
    .center(0, 10).hole(5)            # origin shifts to (0, 10)
    .faces(">Z").workplane()          # origin is STILL (0, 10)!
    .text("HELLO", 8, -0.5)
)
```

- **Fix 1 (recommended):** `.faces(">Z").workplane(origin=(0, 0, height))`
- **Fix 2:** `.faces(">Z").workplane(centerOption="CenterOfBoundBox")`
- **Fix 3 (safest for text), Fresh Workplane Pattern:**
  ```python
  text = cq.Workplane("XY").transformed(offset=(0, y, z), rotate=(0, 0, 90)).text(...)
  body = body.cut(text)  # or .union(text)
  ```
- **Prevention:** use `.moveTo()` instead of `.center()` for a single feature --
  `.moveTo()` does not mutate the plane origin.

## The Fresh Workplane Pattern

To place a feature at a known global coordinate, bypass `.faces().workplane()`
entirely rather than track accumulated origin/orientation state:

```python
feature = cq.Workplane("XY").transformed(offset=(x, y, z), rotate=(rx, ry, rz)).circle(r).extrude(h)
body = body.union(feature)  # or .cut(feature)
```

**Use when:** placing text, adding a feature after a hole/cut moved the implicit
context, or origin drift (above) is a concern. **Don't use when:** the feature
must follow a face's orientation (an angled face) -- there,
`.faces().workplane()` is still right. Still builds through a workplane frame
(`.transformed()`), so it is *not* the "hardcoded global coordinates"
anti-pattern (`CadQuery Anti-Patterns.md`, Tier 2) -- that one is about a
mid-chain `.translate()`.

Text/emboss-specific gotchas (deboss silent failures, additive overflow,
measuring text bounding boxes) live in `reference/emboss_text.md`, appended only
for a part involving text/emboss. The negative-space anti-pattern catalog lives
in `reference/CadQuery Anti-Patterns.md`, appended for every part.
