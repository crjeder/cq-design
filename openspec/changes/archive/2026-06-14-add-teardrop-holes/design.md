## Context

Subtractive blocks in `blocks/connectors.py` (`port_cutout`, `cable_slot`, `vent_grid`) build a solid cutter that the model script subtracts from a wall. The same module defines `_EPS = 1e-4` for overcutting the exit face. Horizontal bores - holes whose axis lies in the build (XY) plane - are not covered by any block. With a plain circle the top of the bore is an unsupported overhang: above roughly 45 degrees from horizontal the upper arc sags and the roof of the hole prints poorly.

The standard FDM fix is a teardrop / drop-shaped profile: keep the lower part circular and replace the upper half with two flat faces that meet at a peak (`^`, roof of a house). Every face of the peak then stays at or below the 45-degree overhang limit, so the bore self-supports. The FDM reference already recommends this verbally; this change provides the geometry as a block.

## Goals / Non-Goals

**Goals:**
- One-call subtractive block producing a self-supporting teardrop bore for a horizontal hole.
- Profile: lower semicircle (full circle below the horizontal centerline) plus an upper `^` peak whose faces sit at the configured angle from horizontal (default 45 degrees).
- Consistent with existing connector blocks: returns a `cq.Workplane` cutter, overcuts the exit face by `_EPS`, units in mm.
- Bore axis convention matches the other wall cutouts so it drops into the same `.cut()` usage.

**Non-Goals:**
- No automatic detection of which holes are horizontal - the model author chooses to use this block.
- No threading, chamfer, or counterbore variants in this change.
- No change to the closed interface-type vocabulary.
- Not modifying `dowel_bore` or other existing holes to become teardrops.

## Decisions

### Profile geometry: semicircle + triangular peak, built as a 2D sketch then extruded
Build the cross-section as a single closed wire on the cutting plane: the lower half is a circular arc of radius `r = d/2` from one side, around the bottom, to the other side at the horizontal centerline; the upper half is two straight segments rising from each end of the diameter to an apex on the vertical axis. Extrude along the bore axis by `depth + _EPS`.

The apex height above center is `r / tan(theta)` is rejected; instead the two roof faces are drawn at `angle` degrees from horizontal so the apex height is `r * tan(angle)` measured from the diameter endpoints inward... the implementation computes the apex from the half-width `r` and `angle` via `apex_y = r * tan(radians(angle))`. With the default `angle = 45`, the apex sits `r` above the centerline and the roof faces are exactly 45 degrees - the printable limit.

Alternative considered: a full circle unioned with a triangle on top (classic "teardrop" with the circle intact and a small cap). Rejected because it leaves a short vertical-ish arc near the centerline that still overhangs slightly and complicates the watertightness test; the clean semicircle-plus-roof profile keeps every upper face at exactly the target angle.

### Module placement: `blocks/connectors.py`
The block is a wall cutout, semantically a sibling of `port_cutout`/`cable_slot`, and reuses that module's `_EPS`. Alternative: a new `blocks/holes.py`. Rejected as premature - one function does not justify a new module; connectors already owns subtractive openings.

### Axis convention
The cutter is built so its bore axis runs along +Y (depth direction), matching `port_cutout`/`cable_slot` which extrude the cut through the wall along Y. The teardrop peak points up (+Z), which is the build-up direction, so "self-supporting" holds when the part is printed in its modeled orientation. The model author rotates the cutter if the hole runs along a different axis - documented in the `use` string.

### Interface type: reuse `axis`
The inventory interface vocabulary is closed (`face_mount, screw_hole, ..., axis, ...`). `axis` is currently unused and fits a through-bore that receives a rod/shaft/pin. The descriptor declares one `axis` interface oriented along the bore (+Y). No vocabulary change needed.

### Parameters
`teardrop_bore(d, depth, angle=45, ...)`:
- `d`: bore diameter in mm (the circular lower portion diameter).
- `depth`: wall thickness to cut through in mm (overcut by `_EPS`).
- `angle`: roof face angle from horizontal in degrees, default 45 (the overhang limit). Larger angles give a sharper, taller peak (more self-supporting margin but more wasted clearance above the round part); smaller angles approach a flat-top slot and risk overhang.

## Risks / Trade-offs

- [Apex angle set too low (< ~40 deg)] -> roof faces exceed the overhang limit and droop. Mitigation: default 45; document the lower bound in the `use` string and validate `0 < angle < 90` is not strictly required but values should stay >= 45 for printability. The block does not hard-clamp; it trusts the author, consistent with other blocks.
- [Author uses the block for a vertical hole] -> wasted peak geometry and a non-round hole where a plain bore would do. Mitigation: `use` string states this is only for horizontal bores; vertical holes should use a plain `.hole()`.
- [Orientation mismatch] -> if the part is printed rotated, the peak no longer points up and self-support is lost. Mitigation: document that the peak points +Z in the modeled frame and the part must print in that orientation (or the cutter be rotated to match the print-up direction).
- [Watertightness near the apex/diameter junction] -> a malformed wire could produce a non-manifold solid. Mitigation: build from a single closed wire (arc + two lines), and the test asserts watertightness.
