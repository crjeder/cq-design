# CadQuery Pattern Reference

## Table of Contents

1. CadQuery Workplane Naming (XY/XZ/YZ)
2. Basic Shapes (Primitives)
3. BRep Vocabulary (Topology Types)
4. Face & Edge Selectors
5. 2D Construction (Wire Drawing)
6. Sketch API
7. Machining Operations (Holes, Shell, Fillet)
8. Advanced 3D Operations (Loft, Sweep, Revolve)
9. Array Methods
10. Transform Operations (Translate, Rotate, Mirror)
11. Boolean Operations
12. Non-Overlapping Part Assembly (Performance)
13. Center Selection
14. Accessing Objects & Debugging
15. Drawing Arcs by Sagitta
16. Common Gotchas
17. Workplane Context Stacking (Origin Drift)
18. The Fresh Workplane Pattern
19. Text & Emboss Reference -- see `reference/emboss_text.md`
20. Anti-Patterns -- see `reference/CadQuery Anti-Patterns.md`


## CadQuery Workplane Naming (XY/XZ/YZ)

`cq.Workplane("XY")`, `"XZ"`, `"YZ"` name the plane a sketch is drawn on, not a
world-frame convention (that's `prompts/planning.md`'s separate North/East/Up
vocabulary for assembly placement) -- this is purely about which two local axes a
2D sketch spans before `.extrude()`/`.revolve()` lifts it into 3D:

- `"XY"` — sketch spans X/Y, extrudes along Z (Z is up); normal = +Z
- `"XZ"` — sketch spans X/Z, extrudes along Y (Y is depth); normal = +Y
- `"YZ"` — sketch spans Y/Z, extrudes along X (X is width); normal = +X

All dimensions are in millimeters.

A workplane is a local 2D coordinate system: an **origin** (local (0,0) in 3D), an
**x-direction**, and a **normal** (the local Z, pointing "out" of the plane). Sketch
operations are defined in that local frame, then lifted into 3D. Ways to create one:

```python
# Named plane, origin at (0,0,0)
cq.Workplane("XY")

# Explicit origin + normal via cq.Plane
cq.Workplane(cq.Plane(origin=(0, 0, 10), normal=(0, 0, 1)))

# On an existing solid's face (origin per centerOption; see Center Selection)
solid.faces(">Z").workplane()

# Offset along the face normal
solid.faces(">Z").workplane(offset=5)

# .transformed() moves the CURRENT plane; cumulative, rotation in local X,Y,Z order
solid.faces(">Z").workplane().transformed(offset=(5, 5, 0), rotate=(0, 0, 45))
```


## Basic Shapes (Primitives)

```python
# Box
cq.Workplane("XY").box(width, depth, height)

# Cylinder
cq.Workplane("XY").cylinder(height, radius)

# Sphere
cq.Workplane("XY").sphere(radius)

# Polygon
cq.Workplane("XY").polygon(6, diameter).extrude(height)  # hexagonal prism

# Ellipse
cq.Workplane("XY").ellipse(x_radius, y_radius).extrude(height)

# Wedge
cq.Workplane("XY").wedge(dx, dy, dz, xmin, zmin, xmax, zmax)
```

## BRep Vocabulary (Topology Types)

CadQuery/OpenCASCADE geometry is a boundary representation (BRep): a hierarchy of
topological entities. The selectors below act on these types.

| Term | Meaning | CadQuery access |
|---|---|---|
| Solid | A closed volume | `.solids()` |
| Shell | A set of connected faces (may be open) | `.shells()` |
| Face | A bounded surface region | `.faces()` |
| Wire | A closed or open loop of edges | `.wires()` |
| Edge | A bounded curve | `.edges()` |
| Vertex | A point | `.vertices()` |
| Compound | A collection of any shapes | `.compounds()` |

## Face & Edge Selectors

### Basic Selectors

```python
# --- Face selectors (based on normal vector) ---
.faces(">Z")   # face with max Z (top)
.faces("<Z")   # face with min Z (bottom)
.faces(">X")   # face with max X
.faces("<X")   # face with min X
.faces(">Y")   # face with max Y
.faces("<Y")   # face with min Y
.faces("+Z")   # face whose normal points in +Z direction
.faces("-Z")   # face whose normal points in -Z direction
.faces("|Z")   # face whose normal is parallel to Z axis
.faces("#Z")   # all faces whose normal is perpendicular to Z axis
.faces("%Plane")     # planar faces only (excludes curved surfaces)
.faces("%Cylinder")  # cylindrical faces (also %Cone, %Sphere, %Torus)

# --- Edge selectors (based on edge direction) ---
.edges("|Z")   # edges parallel to Z axis (vertical edges)
.edges("|X")   # edges parallel to X axis
.edges("|Y")   # edges parallel to Y axis
.edges("#Z")   # edges perpendicular to Z axis
.edges(">Z")   # edges with max Z position
.edges("<Z")   # edges with min Z position
.edges("%Circle")  # circular edges only
.edges("%Line")    # straight edges only

# --- Vertex selectors (based on position) ---
.vertices(">Z")   # vertex with max Z
.vertices("<X")   # vertex with min X
```

### Selector Modifier Reference

| Modifier | Meaning | On faces | On edges |
|---|---|---|---|
| `>` | Maximum | Face at max position | Edge at max position |
| `<` | Minimum | Face at min position | Edge at min position |
| `+` | Positive direction | Face with normal in positive direction | Edge aligned in positive direction |
| `-` | Negative direction | Face with normal in negative direction | Edge aligned in negative direction |
| `|` | Parallel | Normal parallel to axis | Edge parallel to axis |
| `#` | Perpendicular | Normal perpendicular to axis | Edge perpendicular to axis |
| `%` | Type | `%Plane`, `%Cylinder`, `%Cone`, `%Sphere`, `%Torus` | `%Circle`=circle, `%Line`=straight |

### Nth Selector & Compound Selectors

```python
# --- Nth selector (sort by centroid along an axis, pick by 0-based index) ---
.edges(">Z[0]")    # edge with max Z (same as ">Z")
.edges(">Z[1]")    # edge with 2nd highest Z
.faces("<Y[-1]")   # last face from the min-Y end
.faces(">>Z[1]")   # explicit sorted-index form: >> sorts high->low, << low->high
.edges("<<X[0]")   # edge with the lowest X centroid

# --- Custom direction vector ---
.edges(">(-1, 1, 0)")      # edge max in (-1,1,0) direction
.chamfer(1).edges("+(-1, 1, 0)")  # chamfer in specific direction

# --- Logical combinations ---
.edges("|Z and >X")           # parallel to Z AND max X
.edges("|Z or |X")            # parallel to Z OR parallel to X
.faces("not >Z")              # all faces except top
.edges("|Z exc >X")           # parallel to Z, excluding max X (set difference)

# --- Compound selectors ---
.faces(">Z").edges()          # all edges of top face
.faces(">Z").edges("|X")      # X-direction edges of top face
```

### Programmatic Selection

```python
# --- filter: filter with a lambda ---
result.faces().filter(lambda f: f.Area() > 100)

# --- sort: sort + slice ---
result.edges().sort(lambda e: e.Length())[:3]   # 3 shortest edges

# --- Topological selection ---
result.faces(">Z").ancestors("SOLID")    # solid containing the top face
result.edges(">Z").siblings("%Circle")   # sibling circular edges of top-face edges
```

### Selector Semantics (read before trusting a selection)

- **`>Z` tests the centroid, not the highest point.** It returns the face/edge whose
  area-centroid has the max Z, which on a slanted or irregular solid is not necessarily
  the one containing the topmost vertex.
- **`|axis` (parallel) vs `+/-axis` (direction).** `|Z` selects every face whose normal is
  parallel to Z -- on a box that is BOTH the top and bottom face. `+Z` / `-Z` narrow to the
  single face pointing that way. Use `>Z` for "the top face" specifically.
- **`#axis` (orthogonal).** `#Z` selects faces whose normal is orthogonal to Z (the 4 sides
  of a box) and edges whose direction is orthogonal to Z (the horizontal edges).
- **Prefer chaining over a combined string.** `.faces(">Z").edges("%Circle")` (top face,
  then its circular edges) is clearer and more predictable than `.edges("%Circle and >Z")`.

### Tags (stable selection)

Tags are the most stable selection mechanism -- they survive feature additions that shift
index-based selectors. Tag a face/edge as soon as it is created, then re-select it later:

```python
result = (
    cq.Workplane("XY").box(20, 20, 10)
    .faces(">Z").tag("top").end()
    .faces("<Z").tag("bottom").end()
    .faces(tag="top").workplane().hole(4)      # survives fillets/features added in between
    .faces(tag="bottom").workplane().hole(2)
)
```

Tags are stored on the Workplane, not on the shape. `.end()` returns to the solid context
after tagging (see `reference/CadQuery Anti-Patterns.md`, Tier 2).

## 2D Construction (Wire Drawing)

```python
# --- Basic shapes (closed wires) ---
.rect(xLen, yLen)                      # rectangle
.circle(radius)                        # circle
.ellipse(x_radius, y_radius)           # ellipse
.polygon(nSides, diameter)             # regular polygon

# --- Point movement & line drawing ---
.moveTo(x, y)                          # move pen (no drawing)
.lineTo(x, y)                          # line to absolute coordinates
.line(xDist, yDist)                    # line by relative offset
.hLine(distance)                       # horizontal line
.vLine(distance)                       # vertical line
.polarLine(distance, angle)            # line in polar coordinates

# --- Curves ---
.threePointArc((x2, y2), (x3, y3))    # arc through 3 points
.sagittaArc((endX, endY), sag)         # arc with sagitta (height)
.radiusArc((endX, endY), radius)       # arc with given radius
.tangentArcPoint((x, y))               # tangent arc
.spline([(x1,y1), (x2,y2), ...])      # spline curve

# --- Close ---
.close()                               # close back to start point

# --- Example: L-shaped cross-section ---
result = (
    cq.Workplane("XY")
    .moveTo(0, 0)
    .lineTo(10, 0)
    .lineTo(10, 3)
    .lineTo(3, 3)
    .lineTo(3, 10)
    .lineTo(0, 10)
    .close()
    .extrude(5)
)
```

## Sketch API

```python
# Shape constructors: .rect(w,h) .circle(r) .ellipse(a1,a2)
#   .trapezoid(w,h,angle) .regularPolygon(r,n) .polygon([(x,y),...])
result = (
    cq.Workplane("XY")
    .sketch()
    .rect(20, 20)
    .circle(5, mode="s")          # mode: "a" add (default), "s" subtract, "i" intersect
    .push([(0, 0), (20, 0)])      # replicate next op at each point
    .circle(3)
    .finalize()                   # required before returning to Workplane ops
    .extrude(10)
)

# Reusable profile with .placeSketch() -- define once, place at many locations
slot = cq.Sketch().slot(8, 3)          # length, width
result = (
    cq.Workplane("XY")
    .box(40, 20, 8)
    .faces(">Z").workplane()
    .placeSketch(
        slot.moved(cq.Location((-10, 0, 0))),
        slot.moved(cq.Location((10, 0, 0))),
    )
    .cutBlind(-4)
)
```

## Machining Operations (Holes, Shell, Fillet)

```python
# --- Fillet (rounding edges) ---
.edges("|Z").fillet(radius)
.edges().fillet(radius)                # all edges

# --- Chamfer ---
.edges("|Z").chamfer(distance)
.edges().chamfer(length, length2)      # asymmetric chamfer

# --- Holes ---
.faces(">Z").hole(diameter)                              # through hole at center
.faces(">Z").hole(diameter, depth)                       # blind hole
.faces(">Z").cboreHole(hole_d, cbore_d, cbore_depth)     # counterbore hole
.faces(">Z").cskHole(hole_d, csk_d, csk_angle)           # countersink hole

# --- Cut ---
.cutBlind(depth)                       # cut to given depth using current wire
.cutBlind(depth, taper=angle)          # tapered blind cut
.cutThruAll()                          # cut through all using current wire
.cutThruAll(taper=angle)               # tapered through cut
# cutBlind cuts along the workplane normal, which points OUTWARD from a selected
# face -- use invert=True to cut INTO the solid (see Anti-Patterns, Tier 3):
.faces(">Z").workplane(invert=True).rect(5, 5).cutBlind(3)

# --- Extrude combine flag ---
.circle(3).extrude(5)                  # combine=True (default): unioned into the solid
.circle(3).extrude(5, combine=False)   # separate solid (combine/export independently)

# --- Shell (hollow out) ---
.faces(">Z").shell(-wall_thickness)    # hollow with top face open
.shell(-wall_thickness)                # auto-open thinnest face

# --- Positioned holes & bosses ---
.faces(">Z").workplane().pushPoints([(x1,y1), (x2,y2)]).hole(d)
.faces(">Z").workplane().pushPoints([(x1,y1)]).circle(r).extrude(h)

# --- Engraved text ---
.faces(">Z").workplane().text("TEXT", fontsize, depth)
# depth > 0: embossed, depth < 0: engraved
```

## Advanced 3D Operations (Loft, Sweep, Revolve)

```python
# --- Loft (smooth connection between cross-sections) ---
result = (
    cq.Workplane("XY")
    .rect(10, 10)                      # bottom cross-section
    .workplane(offset=10)
    .circle(5)                         # top cross-section
    .loft()                            # ruled=True for straight loft
)

# --- Sweep (extrude along a path) ---
path = cq.Workplane("XZ").spline([(0,0), (10,10), (20,0)])
result = (
    cq.Workplane("XY")
    .circle(1)
    .sweep(path)
)

# --- Revolve ---
result = (
    cq.Workplane("XY")
    .moveTo(10, 0)
    .lineTo(10, 10)
    .lineTo(15, 10)
    .lineTo(15, 0)
    .close()
    .revolve(360, (0, 0, 0), (0, 1, 0))   # 360° around Y axis
)
# revolve(angleDegrees, axisStart, axisEnd)

# --- Twist extrude ---
result = (
    cq.Workplane("XY")
    .polygon(6, 10)
    .twistExtrude(20, 90)              # height 20mm, 90° twist
)
```

## Array Methods

| Method | Description |
|---|---|
| `rarray(xc, yc, xs, ys)` | Rectangular array |
| `polarArray(r, start, angle, count)` | Polar (circular) array |

## Transform Operations (Translate, Rotate, Mirror)

```python
# --- Translate ---
# Applies to a built Shape / finished result, moving it in the GLOBAL frame.
# It is not a mid-chain positioning primitive: calling .translate() inside a
# fluent chain bypasses the workplane system (see reference/CadQuery Anti-Patterns.md,
# Tier 2). To position while building, use .center()/.moveTo() or a fresh workplane.
result = part.translate((dx, dy, dz))

# --- Rotate (axis-specified) ---
result = part.rotate(
    axisStartPoint=(0, 0, 0),
    axisEndPoint=(0, 0, 1),
    angleDegrees=45
)

# --- Rotate about center ---
result = part.rotateAboutCenter(
    axisEndPoint=(0, 0, 1),
    angleDegrees=45
)

# --- Mirror ---
result = part.mirror("XY")            # mirror across XY plane
result = part.mirror("YZ")            # mirror across YZ plane
result = part.mirror("XZ")            # mirror across XZ plane

# --- Split ---
result = part.split()                  # split at current workplane
```

## Boolean Operations

```python
# Union
result = part_a.union(part_b)

# Difference (subtract)
result = part_a.cut(part_b)

# Intersection
result = part_a.intersect(part_b)

# Combine all on stack
result = wp.combine()                  # union all objects on the stack
```

### Assembly (Multi-part Layout Check)

```python
assembly = cq.Assembly()
assembly.add(bottom, name="bottom", color=cq.Color("gray"))
assembly.add(top, name="top", loc=cq.Location((0, 0, total_h)), color=cq.Color("blue"))
```

## Non-Overlapping Part Assembly (Performance)

For plates/arrays where parts don't touch, skip `.union()` (O(n²) OCCT booleans) and
combine them into one compound instead:

```python
from cadquery import Compound
parts = [gauge1, gauge2, ...]  # list of CQ Workplane objects
compound = Compound.makeCompound([p.val() for p in parts])
cq.exporters.export(compound, "plate.stl")
```

This is 5-10x faster than unioning for 20+ parts. `makeCompound()` works directly on
CQ Workplane `.val()` objects; for raw OCC solids (e.g. after `.moved()` or a
`Location` transform with no Workplane wrapper), build a `TopoDS_Compound` via
`BRep_Builder` instead.

## Center Selection

`centerOption` controls where `.workplane()` puts the origin on a selected face:

| Value | Origin location |
|---|---|
| `"CenterOfMass"` | Center of mass of the face |
| `"CenterOfBoundBox"` | Center of the face's bounding box |
| `"ProjectedOrigin"` | Parent workplane's origin projected onto the new plane (**default**) |

```python
# Create workplane at face center of mass
result.faces(">Z").workplane(centerOption="CenterOfMass")

# Explicit is always safer than the ProjectedOrigin default on irregular faces
result.faces(">Z").workplane(centerOption="CenterOfBoundBox")
```

Never assume the default matches your intent -- for a symmetric face it rarely matters,
but on an irregular face `ProjectedOrigin` can land far from where you expect (see
`reference/CadQuery Anti-Patterns.md`, Tier 2, origin drift).

## Accessing Objects & Debugging

| Method | Description |
|---|---|
| `val()` | Get the current object from the Workplane stack |
| `findSolid()` | Get the nearest Solid object |

## Drawing Arcs by Sagitta

`.sagittaArc(endPoint, sag)` draws an arc from current point to endPoint:
- **Positive sag**: arc bows LEFT of travel direction
- Going left→right: positive sag = arc bows upward (convex)
- Sagitta formula: `sag = R - sqrt(R² - (chord/2)²)`

## Common Gotchas

1. **Outer edge fillets before shell, small/detail fillets after** — apply large exterior fillets (e.g. `edges("|Z")`) before shelling; defer small or interior fillets until after shelling, as pre-existing small fillets can cause shell to fail
2. **Fillet radius must be smaller than the shortest edge** it touches
3. **Boolean cuts must fully intersect** — add 0.01mm extra depth to ensure clean cuts
4. **`.center()` is cumulative** — each call offsets from the CURRENT center, not origin
5. **Use `forConstruction=True`** for reference geometry that shouldn't become solid
6. **Workplane offset** — `.workplane(offset=10)` creates a new workplane 10mm above current
7. **Workplane origin stacking** — `.center(x, y)` permanently mutates the plane origin. Subsequent `.faces().workplane()` inherits the shifted origin via `ProjectedOrigin` (the default `centerOption`). This causes features placed later to be offset. See Workplane Context Stacking section below.
8. **`combine='cut'` text deboss fails silently** — CadQuery's `.text(..., combine='cut')` often produces no change. Use a fresh workplane + explicit `.cut()` instead. See `reference/emboss_text.md`.
9. **Additive text overflows body** — `.text(..., combine='a')` can create geometry outside the body outline. Clip with `.intersect()` or use deboss instead. See `reference/emboss_text.md`.
10. **Prefer boolean subtraction over `.shell()` for enclosures** — for parametric shelled boxes, modeling the cavity as a separate solid and `.cut()`-ing it is more robust than `.shell(-t)`, which frequently fails on filleted bodies or picks the wrong face to open. Reserve `.shell()` for simple uniform-wall cases. Order: outer shape → exterior fillets → cut cavity → holes/cutouts. This is *not* in tension with "prefer feature ops over booleans" (see `reference/CadQuery Anti-Patterns.md`, Tier 1): the skill rule is feature ops for bosses/holes/edges, booleans for combining separate solids AND for cavities/enclosures where `.shell()` is fragile.
11. **Revolved profiles on non-XY workplanes** — `.transformed(offset=(a,b,c))` on XZ or YZ workplanes maps offset to the LOCAL frame, not world coordinates. On an XZ workplane, local-Y is world-Z and the normal is world-Y. A revolve tool placed with `offset=(cx, top_z, cy)` on XZ ends up at world (cx, cy, top_z) — which may be wrong if you assumed world mapping. For revolved chamfer/fillet tools, prefer building on XY and translating the result, or verify with `verify_boolean` that the cut actually changed the geometry.
12. **A feature unioned in AFTER a cavity cut can poke through the cavity floor/wall into the hollow interior** — `union()`-ing a full-height boss, tab, or dovetail onto a body that already has a pit/pocket/shell cavity is only safe where that XY footprint sits *outside* the cavity's footprint. Where it overlaps the cavity, the feature's full height extends past the remaining solid material and pokes into open space — invisible from every exterior view (the feature is still flush with the outer wall) and visible only in a cross-section that happens to cut through it. Clip the unioned feature's height/extent to the actual solid thickness at that XY position (e.g. a seam tab that reaches under a pit: extrude it only from the print bed up to the cavity floor, not to the part's full height), don't assume "runs the height of the part" is safe once any cavity exists. Visual self-review must check this explicitly (see `reference/Visual Review Checklist.md` item 8) — the exterior renders look identical whether or not the feature is clipped correctly.

## Workplane Context Stacking (Origin Drift)

`.center(x, y)` calls `plane.setOrigin2d()` which **permanently mutates** the workplane origin. When you later call `.faces(">Z").workplane()`, the default `centerOption="ProjectedOrigin"` projects the *current* (shifted) origin onto the new face — NOT the face center.

**Example of the bug:**
```python
result = (
    cq.Workplane("XY").box(40, 40, 10)
    .faces(">Z").workplane()
    .center(0, 10).hole(5)           # origin shifts to (0, 10)
    .faces(">Z").workplane()          # origin is STILL (0, 10)!
    .text("HELLO", 8, -0.5)          # text placed 10mm off-center
)
```

**Fix 1 (recommended): Explicit origin reset**
```python
.faces(">Z").workplane(origin=(0, 0, height))
```

**Fix 2: Use CenterOfBoundBox**
```python
.faces(">Z").workplane(centerOption="CenterOfBoundBox")
```

**Fix 3: Fresh workplane (safest for text)**
```python
text = cq.Workplane("XY").transformed(offset=(0, y, z), rotate=(0, 0, 90)).text(...)
body = body.cut(text)  # or .union(text)
```

**Prevention:** Use `.moveTo()` instead of `.center()` when you only need to reposition a single feature. `.moveTo()` does NOT mutate the plane origin.

## The Fresh Workplane Pattern

When placing a feature at a known global coordinate, bypass `.faces().workplane()`
entirely rather than tracking accumulated origin/orientation state:

```python
feature = (
    cq.Workplane("XY")
    .transformed(offset=(x, y, z), rotate=(rx, ry, rz))
    .circle(r).extrude(h)
)
body = body.union(feature)  # or .cut(feature)
```

**Use when:** placing text, adding a feature after a hole/cut has already moved the
implicit context, or any time workplane origin drift (see the section above) is a
concern.

**Don't use when:** the feature must follow a face's orientation (e.g. a feature on
an angled face) -- there, `.faces().workplane()` is still the right tool.

This still builds through a workplane frame (`.transformed()`), so it is *not* the
"hardcoded global coordinates" anti-pattern (`reference/CadQuery Anti-Patterns.md`,
Tier 2) -- that one is about positioning with a mid-chain `.translate()`.

## Text & Emboss Reference

The basic `.text()` idiom is under Machining Operations above. The deeper
text-specific gotchas (deboss silent failures, additive-text overflow, measuring
text bounding boxes) live in `reference/emboss_text.md`, appended to
`{{CQ_REFERENCE}}` only for a part that involves text/emboss.

## Anti-Patterns

The negative-space catalog -- the mistakes LLMs make generating CadQuery and how to fix
them -- lives in `reference/CadQuery Anti-Patterns.md`, a separate injected file (like
`emboss_text.md`) appended to `{{CQ_REFERENCE}}` for **every** part. It is organized by
durability tier: kernel-level OCCT truths, stateful-context footguns, and CadQuery API
mechanics.

