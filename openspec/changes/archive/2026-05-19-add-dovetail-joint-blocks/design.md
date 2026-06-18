## Context

The `blocks/` library provides CadQuery primitives as importable Python functions. Each function returns a `cq.Workplane` positioned with its base at Z=0, centered in X. Callers translate, rotate, and boolean-combine these. The dovetail joint geometry is derived from [winksaville/cq-box-with-dovetail-lid](https://github.com/winksaville/cq-box-with-dovetail-lid) (MIT license).

## Goals / Non-Goals

**Goals:**
- `dovetail_groove` returns a Workplane to subtract from a body's top edge
- `dovetail_tongue` returns a Workplane that IS the lid panel (no separate lid shape needed)
- Lid sits flush: tongue height = `depth`, so top of tongue = top of box when groove is cut from top
- Both are parameterized by `width` (outer box width), `wall` (wall thickness), `depth`, `length`, `angle`, with `clearance` on the tongue
- Groove opening = `width - 2*wall`; tongue top = `width - 2*wall - 2*clearance`
- Two matching inventory.json entries with `sliding_interface` interface type

**Non-Goals:**
- No complete box-with-lid assembly model (that's a consumer of these blocks)
- No support for angled or non-rectangular boxes
- No through-dovetail (press-fit) variant

## Decisions

### Coordinate system: base at Z=0, opening at Z=depth, slides along +Y

Consistent with all existing blocks (`fillet_box`, `hollow_box`, etc.). The groove's wide base is at Z=0 and its narrow opening is at Z=depth. The tongue mirrors this. Caller places the groove at `z = box_h - depth` to make the lid sit flush.

Alternative considered: opening at Z=0, base at Z=depth (opening faces down, base faces up). Rejected because it breaks the convention that Z=0 is the reference face placed by the caller.

### Extrusion plane: XZ workplane, extrude along +Y

The cross-section lives in XZ. `.extrude(length)` on an XZ workplane extends along +Y, matching the "slides in from front" assembly pattern. Caller places the groove at the appropriate Y offset (typically `y = -box_d/2 + wall` for a centered box).

### Clearance on tongue only, not on groove

The groove is cut at nominal size. The tongue is shrunk by `2*clearance` on its top width (both angled sides shift inward by `clearance`). This is the standard practice: one part is nominal, the mating part carries the tolerance. Matches the source reference.

### `dovetail_tongue` IS the lid panel

The tongue's cross-section has height=`depth` (= `lid_t`). It is the full lid geometry — no separate flat panel. Callers that want a decorative top face can union a thin face sheet on top. This keeps the block minimal and composable.

### Wall thickness is a first-class parameter

`wall` is accepted by both functions and used to derive the groove opening from the outer box width: `inner = width - 2*wall`. This mirrors how `hollow_box` takes `w` (outer) and `wall`, and means the caller passes raw box dimensions without doing the subtraction externally. Typical usage: `width=box_w`, `wall=box_wall`, `length=box_d - box_wall`.

### Geometry

```
inner = width - 2 * wall
flare = tan(radians(90 - angle)) * depth

Groove XZ points (centered, CCW):
  (-inner/2,        depth)   top-left  (opening edge)
  (-(inner/2+flare), 0)      base-left  (locked base)
  (+(inner/2+flare), 0)      base-right
  (+inner/2,        depth)   top-right

Tongue XZ points (clearance applied symmetrically):
  (-(inner/2 - clearance),        depth)
  (-(inner/2 - clearance + flare), 0)
  (+(inner/2 - clearance + flare), 0)
  (+(inner/2 - clearance),        depth)
```

Default angle=55° from vertical → 35° overhang from horizontal → printable without supports.

## Risks / Trade-offs

- **CadQuery XZ extrusion direction**: `.extrude()` from an `XZ` workplane goes in +Y. This is consistent with the source reference but not explicitly documented. Verified by reading the source code (`extrude(distance=-(yLen - wallThickness))` goes in -Y with a negative distance). If CadQuery version changes this behavior, the extrusion direction would flip. → Tests against bounding-box geometry will catch this.
- **Tongue = full lid**: A caller that wants a lid with features (logo, vent holes) must build on top of this block. The block intentionally does not include such features — callers compose. → Document clearly in `use` field and docstring.
- **No back-wall constraint**: The groove and tongue have length=`d - wall` in a typical assembly; nothing enforces this. The caller is responsible for sizing. → Document in inventory `use` field.

## Open Questions

None — all design decisions are resolved.
