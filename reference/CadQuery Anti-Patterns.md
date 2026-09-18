# CadQuery Anti-Patterns

Mistakes LLMs make generating CadQuery, and how to fix them. Tiers: **1 Kernel-level
(OCCT)** -- geometry facts true in any OpenCASCADE-backed API. **2 Stateful-context**
-- bugs from the fluent API's persistent origin and selection stack. **3 API
mechanics** -- method-specific semantics. Millimeters; fluent API only
(`cadquery.func` not covered). Each `##` section is tagged
`<!-- applies_to: ... -->`, same convention as `CadQuery Pattern Reference.md`.
Two mistakes that used to have a dedicated entry here -- looping a boolean, and
an unresolved `.center()`/`.hole()` origin shift -- are now caught mechanically
by `script_lint.py` (`boolean_in_loop`, `unanchored_feature`) with a fix hint,
and are explained in full in `CadQuery Pattern Reference.md` ("Non-Overlapping
Part Assembly" and "Workplane Context Stacking" respectively), so their entries
were removed here rather than kept as a third copy.


## Tier 1 -- Kernel-level (OCCT geometry truths)
<!-- applies_to: always -->

### Feature operations vs. booleans -- and when each is right

Reaching for `.union()`/`.cut()` when a feature op would be cleaner is the most
common LLM reflex. Booleans rebuild the full boundary; feature ops extend the
existing BRep directly -- faster, cleaner topology.

| Instead of... | Use... |
|--------------|--------|
| `.union(cylinder(...))` for a boss | `.faces(...).workplane().circle(r).extrude(h)` |
| `.cut(cylinder(...))` for a hole | `.faces(...).hole(diameter)` |
| `.cut(box(...))` for a pocket | `.faces(...).workplane().rect(w, h).cutBlind(depth)` |
| `.union(...)` for a chamfered edge | `.edges(...).chamfer(d)` |
| `.union(...)` for a filleted edge | `.edges(...).fillet(r)` |

**Skill rule (reconciles with Pattern Reference Common Gotcha #10):** feature ops for
bosses/holes/pockets/edges on an existing solid; booleans for combining separate
solids, AND for cavities where `.shell()` is fragile on filleted bodies -- model the
cavity as its own solid and `.cut()` it (what `hollow_box` does; see Gotcha #10).
"Avoid booleans" means don't use one for a single boss/hole, not "never cut a cavity."

### A wire must be closed before it can bound a solid

`.lineTo()`/`.spline()`/`.threePointArc()` sequences must reach `.close()` before
`.extrude()`/`.revolve()`, or the profile can't bound a face.

```python
# Wrong: ...lineTo(0, 5).extrude(3)          # no .close() -> open shell
# Right:  ...lineTo(0, 5).close().extrude(3)
```

### `BREP_API command not done`

An OCCT BRep op could not be completed geometrically -- not a CadQuery bug; the
message doesn't say which op failed. Common causes:

- **Fillet/chamfer radius too large** -- larger than the shortest adjacent edge, or
  adjacent fillets overlap. Reduce radius; smallest features first, separate calls
  per edge group.
- **Self-intersecting profile/sweep** -- a wire crossing itself, a revolve profile
  crossing its own axis, or a sweep profile too large for the path curvature.
- **Shell thickness too large** -- `.shell()` fails when thickness exceeds the
  smallest local radius of curvature. Reduce thickness or simplify first.

```python
solid.edges("|Z").fillet(5)   # Wrong if any |Z edge is shorter than 5, or fillets intersect
# Right: smaller fillets on shorter edges first, then the rest
result = cq.Workplane("XY").box(20,20,5).edges("|Z").fillet(1).edges(">Z").fillet(0.5)
```


## Tier 2 -- Stateful-context footguns
<!-- applies_to: always -->

### Losing the solid context after a selector

After `.faces(...)`/`.edges(...)`, the stack holds the selection, not the solid.

```python
solid.faces(">Z").box(5, 5, 3)                              # Wrong: wrong context
solid.faces(">Z").workplane().rect(5, 5).extrude(3)         # Right: .workplane() re-establishes sketch context
solid.faces(">Z").tag("top").end().faces("<Z").workplane().hole(3)  # Right: .end() returns to solid
```

`.hole()`, `.shell()`, `.fillet()` act on the selected face directly; sketch-then-lift
ops (`.circle().extrude()`, `.rect().cutBlind()`) need `.workplane()` first, or they
silently use whatever plane was active before the selection. When in doubt, call
`.workplane()`.

### Coordinates are local after `.workplane()`

Sketch coordinates are in the plane's **local** frame, not global. `.circle(3)`
lands at local (0,0) (the face center). Shift with `.center()`/`.transformed()`.

### `.val()` silently returns only the first stack item

```python
face  = solid.faces().val()      # Wrong for "give me all": ONE face, first in iteration order
faces = solid.faces().vals()     # Right: all six
```

### `.each()` replaces the stack and needs a Shape return

Calls the callback on every stack item and *replaces* the stack with the returned
Shapes -- not a side-effect iterator.

```python
solid.faces().each(lambda f: print(f.Area()))    # Wrong: returns None, destroys the stack
centers = solid.faces().each(lambda f: f.Center())  # Right: return a Shape per item
```

### `.translate()` on a Workplane moves in global coordinates

`.translate()` is a Shape method; called mid-chain on a Workplane it still moves the
geometry, but in the global frame, bypassing the workplane system.

```python
cq.Workplane("XY").box(10,10,10).translate((5,0,0))       # Wrong: bypasses workplane frame
cq.Workplane("XY").center(5,0).box(10,10,10)               # Right: position via workplane
shape = cq.Workplane("XY").box(10,10,10).val(); shape.translate(cq.Vector(5,0,0))  # Right: fine on an extracted Shape
```

### Index-selector fragility

`">>Z[1]"`/`">Z[1]"` depend on a sorted count of all matching entities. Fillets,
chamfers, holes, or shells change that count and silently shift the selected entity.
Tag the target before adding topology-changing features:

```python
result = (cq.Workplane("XY").box(20,20,20)
          .faces(">Z[1]").tag("target").end()   # tag first
          .edges(">Z").fillet(1)                # would shift the index above
          .faces(tag="target").workplane().hole(3))
```

### Building in hardcoded global coordinates

Absolute global placement (`.translate()`) is brittle; build relative to existing
faces instead. For a genuinely known global placement, use the Fresh Workplane
Pattern (`transformed(offset=...)`) -- still through a workplane frame.


## Tier 3 -- CadQuery API mechanics
<!-- applies_to: always -->


### `.extrude()` defaults to `combine=True`

Unions the new solid into the context stack by default. Pass `combine=False` for a
separate solid. Inverse mistake: relying on the default union, then unioning again ->
double union.

```python
result   = solid.faces(">Z").workplane().circle(3).extrude(5)         # unioned in
new_part = cq.Workplane("XY").circle(3).extrude(5, combine=False)     # separate solid
```

### `.cutBlind()` cuts along the outward face normal

Cuts in the direction of the workplane normal, which points *outward* from a
selected face by default -- cutting from the top face without inverting cuts away
into empty space. Use `.workplane(invert=True)` to flip the normal into the solid.

```python
solid.faces(">Z").workplane().rect(5,5).cutBlind(3)              # Wrong: cuts upward, away from solid
solid.faces(">Z").workplane(invert=True).rect(5,5).cutBlind(3)   # Right: inverted, cuts into solid
```

### `|Z` when you mean `>Z` (and other selector-string confusions)

`|Z` selects every face *parallel* to Z -- on a box, top AND bottom. Use `>Z`
(highest centroid) for "top face only." Related traps: `>Z` picks the max-centroid
entity, not the topmost vertex; `.edges("%Circle and >Z")` (combined string) is less
predictable than `.faces(">Z").edges("%Circle")` (chained). See "Selector Semantics"
in the pattern reference.

```python
solid.faces("|Z")   # top AND bottom -- probably not what you want
solid.faces(">Z")   # top face only
```

### Fluent and Free Function APIs do not mix

A `Workplane` is not a `Shape`; Free Function ops don't accept `Workplane` and vice
versa. Extract with `.val()`/`.vals()` first if you touch `cadquery.func` (fluent-only pipeline).
