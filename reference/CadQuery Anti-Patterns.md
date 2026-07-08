# CadQuery Anti-Patterns

Negative-space companion to `CadQuery Pattern Reference.md`: the mistakes LLMs make
generating CadQuery, and how to fix them. The pattern reference tells you how to do X;
this file tells you what you did wrong.

Organized by **durability tier**, because that ordering is also a real sort -- kernel
truths vs. artifacts of the stateful fluent API:

- **Tier 1 -- Kernel-level (OCCT):** geometry facts. True in any OpenCASCADE-backed API.
- **Tier 2 -- Stateful-context:** bugs that exist *because* the fluent API carries a
  persistent origin and a selection stack. A stateless/algebra-mode API has none of them.
- **Tier 3 -- CadQuery API mechanics:** method-specific semantics you re-express, not
  geometry truths.

All dimensions are in millimeters. Every example is fluent API; the Free Function API
(`cadquery.func`) is intentionally not covered -- this pipeline is fluent-only.


## Tier 1 -- Kernel-level (OCCT geometry truths)

These are OpenCASCADE facts, not CadQuery-API facts.

### Feature operations vs. booleans -- and when each is right

Reaching for `.union()` / `.cut()` when a direct feature operation would be cleaner is the
most common LLM reflex. Booleans rebuild the full boundary from scratch; feature operations
extend or modify the existing BRep directly -- faster, and cleaner topology for subsequent
selections.

| Instead of... | Use... |
|--------------|--------|
| `.union(cylinder(...))` for a boss | `.faces(...).workplane().circle(r).extrude(h)` |
| `.cut(cylinder(...))` for a hole | `.faces(...).hole(diameter)` |
| `.cut(box(...))` for a pocket | `.faces(...).workplane().rect(w, h).cutBlind(depth)` |
| `.union(...)` for a chamfered edge | `.edges(...).chamfer(d)` |
| `.union(...)` for a filleted edge | `.edges(...).fillet(r)` |

**Skill rule (reconciles this with Pattern Reference Common Gotcha #10):**
- **Feature ops** for bosses, holes, pockets, and edges on an existing solid.
- **Booleans** for combining genuinely separate solids, AND for cavities / enclosures
  where `.shell()` is fragile on filleted bodies -- model the cavity as its own solid and
  `.cut()` it (this is exactly what the `hollow_box` block does; see Gotcha #10).

So "avoid booleans" is not absolute: it means *don't* use a boolean for a single boss or
hole; it does *not* mean avoid the sanctioned cavity-cut pattern.

### Booleans are expensive -- never loop them

Each boolean recomputes the full boundary. N sequential cuts is O(N) full-boundary rebuilds.
Combine the tools into one compound and subtract once.

```python
# Wrong: 10 sequential boolean operations
result = body
for h in holes:            # each iteration rebuilds the whole boundary
    result = result.cut(h)

# Right: one compound, one cut
from cadquery import Compound
tool = Compound.makeCompound([h.val() for h in holes])
result = body.cut(tool)
```

This is the same principle behind the pattern reference's "Non-Overlapping Part Assembly"
section (compound instead of N unions).

### A wire must be closed before it can bound a solid

`.lineTo()` / `.spline()` / `.threePointArc()` sequences must reach `.close()` before
`.extrude()` or `.revolve()`. An open wire cannot bound a face, so it errors or produces an
open shell.

```python
# Wrong: missing .close() -> extrude has no closed profile
cq.Workplane("XY").moveTo(0, 0).lineTo(10, 0).lineTo(10, 5).lineTo(0, 5).extrude(3)

# Right
cq.Workplane("XY").moveTo(0, 0).lineTo(10, 0).lineTo(10, 5).lineTo(0, 5).close().extrude(3)
```

### `BREP_API command not done`

This comes from the OpenCASCADE kernel: a BRep operation could not be completed
geometrically. It is not a CadQuery bug -- the requested geometry is invalid or degenerate.
The message does not say which operation failed. Common causes:

- **Fillet / chamfer radius too large** -- larger than the shortest adjacent edge, or
  adjacent fillets overlap. Reduce the radius; fillet in separate calls, smallest features
  first; fillet different edge groups separately rather than all at once.
- **Self-intersecting profile** -- a wire/sketch that crosses itself, or a revolve profile
  that crosses its own axis of revolution, cannot be extruded/revolved.
- **Self-intersecting sweep** -- the profile is too large relative to the path curvature and
  folds back on itself at tight bends. Reduce the profile size or increase the path radius.
- **Shell thickness too large** -- `.shell()` fails when the thickness exceeds the smallest
  local radius of curvature (the offset surface self-intersects). Reduce thickness or
  simplify the geometry before shelling.

```python
# Fails if the box edge is shorter than 5, or adjacent fillets intersect
solid.edges("|Z").fillet(5)   # BREP_API command not done

# Apply smaller fillets to shorter edges first
result = (cq.Workplane("XY").box(20, 20, 5)
          .edges("|Z").fillet(1)      # vertical edges first
          .edges(">Z").fillet(0.5))   # then top perimeter, smaller radius
```


## Tier 2 -- Stateful-context footguns

Every item here is a consequence of the fluent API's persistent origin and selection stack.
A stateless / algebra-mode API (e.g. build123d algebra mode) has none of these failure modes.

### Origin drift after `.center()`

`.center(x, y)` permanently mutates the workplane origin. A later `.faces(">Z").workplane()`
inherits that shifted origin via the default `centerOption="ProjectedOrigin"` -- NOT the face
center -- placing subsequent features off-center. Full treatment, with three fixes, lives in
the pattern reference's **"Workplane Context Stacking (Origin Drift)"** and **"The Fresh
Workplane Pattern"** sections. Prefer `.moveTo()` (does not mutate the origin) when
repositioning a single feature.

### Losing the solid context after a selector

After `.faces(...)` or `.edges(...)`, the stack holds the selected entities, not the solid.
Calling a feature op directly on the selection uses the wrong context.

```python
# Wrong: after .faces(), the solid is not the active context
solid.faces(">Z").box(5, 5, 3)

# Right: .workplane() re-establishes a sketch context on the face
solid.faces(">Z").workplane().rect(5, 5).extrude(3)

# Right: .end() returns to the solid context
solid.faces(">Z").tag("top").end().faces("<Z").workplane().hole(3)
```

Which ops need a `.workplane()` after a face selection: `.hole()`, `.shell()`, and
`.fillet()` act on the selected face directly, but sketch-then-lift ops
(`.circle().extrude()`, `.rect().cutBlind()`) need one -- skipping it silently uses whatever
plane was active *before* the selection, producing geometry in the wrong place. When in
doubt, call `.workplane()`.

```python
solid.faces(">Z").hole(3)                       # fine -- .hole() works on the face directly
solid.faces(">Z").circle(3).extrude(5)          # wrong -- uses the previous plane context
solid.faces(">Z").workplane().circle(3).extrude(5)   # correct
```

### Coordinates are local after `.workplane()`

Once a workplane is attached, all sketch coordinates are in that plane's **local** frame,
not global. A `.circle(3)` lands at the face center (local (0,0)), not global (0,0). Shift
within the local frame with `.center()` or `.transformed()` -- not by reaching for global
coordinates.

```python
solid.faces(">Z").workplane().circle(3).extrude(5)              # circle at face center
solid.faces(">Z").workplane().center(10, 10).circle(3).extrude(5)  # shifted in local frame
```

### `.val()` silently returns only the first stack item

`.val()` returns the first item and discards the rest without error. Use `.vals()` for all.

```python
face  = solid.faces().val()    # ONE face, first in iteration order -- not necessarily ">Z"
faces = solid.faces().vals()   # all six
top   = solid.faces(">Z").val()  # select first, then val() for a specific one
```

### `.each()` replaces the stack and needs a Shape return

`.each(callback)` calls the callback on every stack item and *replaces* the stack with the
returned Shapes. It is not a side-effect iterator.

```python
# Wrong: callback returns None; stack is destroyed
solid.faces().each(lambda f: print(f.Area()))

# Right (transform): return a Shape per item
centers = solid.faces().each(lambda f: f.Center())

# For inspection, iterate .vals() instead
for face in solid.faces().vals():
    print(face.Area())
```

### `.translate()` on a Workplane moves in global coordinates

`.translate()` is a Shape method. Called mid-chain on a Workplane it still moves the geometry,
but in the global frame -- bypassing the workplane system. Position with workplane placement
instead; use `.translate()` only on an extracted Shape or a finished `result` (see the
pattern reference's Transform Operations note).

```python
# Bypasses the workplane frame
cq.Workplane("XY").box(10, 10, 10).translate((5, 0, 0))

# Position via the workplane instead
cq.Workplane("XY").center(5, 0).box(10, 10, 10)

# .translate() is fine on an extracted Shape
shape = cq.Workplane("XY").box(10, 10, 10).val()
moved = shape.translate(cq.Vector(5, 0, 0))
```

### Index-selector fragility

`">>Z[1]"` / `">Z[1]"` depend on a sorted count of all matching entities. Adding fillets,
chamfers, holes, or shells changes that count and silently shifts which entity is selected.
Tag the target before adding features that change topology.

```python
result = (cq.Workplane("XY").box(20, 20, 20)
          .faces(">Z[1]").tag("target")   # tag first
          .end()
          .edges(">Z").fillet(1)          # this would shift the index above
          .faces(tag="target").workplane().hole(3))
```

Note: the fragility *principle* is broader than the fluent API (any position-sorted index
can shift), but the tag-based fix here is fluent-specific.

### Building in hardcoded global coordinates

Placing everything at absolute global coordinates makes scripts brittle. Build relative to
existing faces. When you *do* need a known global placement, use the Fresh Workplane Pattern
(`transformed(offset=...)`) -- that still works through a workplane frame and is not this
anti-pattern.

```python
# Brittle: positions hardcoded in global space via translate()
result = (cq.Workplane("XY").box(30, 30, 10)
          .union(cq.Workplane("XY").cylinder(5, 8).translate((10, 10, 9))))

# Relative to the face
result = (cq.Workplane("XY").box(30, 30, 10)
          .faces(">Z").workplane().center(10, 10).circle(5).extrude(8))
```


## Tier 3 -- CadQuery API mechanics

Method-specific semantics. Not deleted by a stateless API, but re-expressed differently.

### `.extrude()` defaults to `combine=True`

By default `.extrude()` unions the new solid into the context stack. Pass `combine=False`
for a separate solid (to combine later or export independently). The inverse mistake also
occurs: relying on the default union, then unioning the result again -> double union.

```python
result   = solid.faces(">Z").workplane().circle(3).extrude(5)              # unioned in
new_part = cq.Workplane("XY").circle(3).extrude(5, combine=False)          # separate solid
```

### `.cutBlind()` cuts along the outward face normal

`.cutBlind(depth)` cuts in the direction of the workplane normal, which points *outward* from
a selected face by default -- so cutting from the top face without inverting cuts away into
empty space. Use `.workplane(invert=True)` to flip the normal into the solid.

```python
# Wrong: cuts upward, away from the solid
solid.faces(">Z").workplane().rect(5, 5).cutBlind(3)

# Right: invert the normal to cut into the solid
solid.faces(">Z").workplane(invert=True).rect(5, 5).cutBlind(3)
```

### `|Z` when you mean `>Z` (and other selector-string confusions)

The most common wrong-face bug: `|Z` selects every face whose normal is *parallel* to Z --
on a box that is the top AND the bottom face. For "the top face only" use `>Z` (highest
centroid). Related traps: `>Z` picks the max-*centroid* entity, not the one with the topmost
vertex; and `.edges("%Circle and >Z")` (combined string) is less predictable than
`.faces(">Z").edges("%Circle")` (chained). See the "Selector Semantics" subsection in the
pattern reference.

```python
solid.faces("|Z")   # top AND bottom -- probably not what you want
solid.faces(">Z")   # top face only
```

### Fluent and Free Function APIs do not mix

A `Workplane` is not a `Shape`; Free Function operations do not accept `Workplane` objects,
and Shape operators do not accept `Workplane`. If you ever touch `cadquery.func`, extract
with `.val()` / `.vals()` first. (This pipeline is fluent-only, so prefer to stay in the
fluent API entirely.)
