## Context

`blocks/joints.py` already has a knuckle hinge (`hinge_leaf`) built on a private
tiled-cylinder core (`_cylinder_along_y`), and a two-axis functional taxonomy
(`motion`, `reversible`, `carries`) recorded in `inventory.json`. The previous joint
pass (`expand-joint-blocks`) explicitly listed the living hinge as a non-goal because
its flexure is anisotropy- and material-dependent. This change revisits that, and adds
two adjacent features users keep reaching for: a filament-pinned compact hinge and a
shadow-gap seam detail.

The three blocks are not one mechanism. They share the seam/fold role and the existing
conventions (`_EPS` overcut for subtractive geometry, a `clearance`/fit modifier where
a fit exists, mate-pair naming) but not a single construction core:

- `filament_hinge` reuses the existing tiled-cylinder core (`_cylinder_along_y`).
- `living_hinge` is a flat panel + thin-web extrusion (no revolve, no tile).
- `shadow_gap` is an extruded L-section lip (no revolve, no tile).

## Goals / Non-Goals

**Goals:**
- A compact print-in-place hinge sized for a 1.75 mm filament pin, returned as one
  flat body (distinct from `hinge_leaf`, which returns one leaf for two separate parts).
- A continuous living-hinge flexure with a documented print orientation and material
  caveat, since the prior pass deferred it only for lack of that documentation.
- A `shadow_gap` edge detail that turns an unavoidable butt-joint gap into a clean,
  deliberate, uniform recessed reveal with the real seam concealed.
- Honest inventory taxonomy and one new interface type (`seam`) for the shadow gap.

**Non-Goals:**
- No segmented/lattice ("Bambu-style") living hinge with relief slots in this pass;
  the single continuous web is the minimal working form.
- No auto-placement of the shadow-gap mating cut on the back part (placed manually,
  consistent with all other blocks).
- No material database or per-filament flex-life modeling; orientation and material
  guidance lives in the `use` string only.
- No change to the runner, part loop, BUILD_PLAN schema, or quality gate.

## Decisions

**`filament_hinge` returns the whole hinge as one flat print-in-place body.**
`hinge_leaf` returns a single leaf (side A or B) so two separately printed parts can
be hinged. `filament_hinge` instead returns both leaves with their knuckles
interleaved on a shared axis, coplanar (opened flat at 180 deg), as one solid that
prints in place. After printing, a snipped length of 1.75 mm filament is pushed
through the coaxial bore as the pivot pin. This is why it is a distinct block, not a
preset of `hinge_leaf`: the return value (one combined body vs one leaf) differs.

- Signature: `filament_hinge(length, knuckles, leaf_w, leaf_t, d_filament=1.9, clearance=0.25)`.
- Construction: reuse `_cylinder_along_y` for the knuckles; alternate A/B knuckle
  bands along +Y exactly as `hinge_leaf` does; place the two flat leaves on opposite
  sides of the axis in the same plane; bore one coaxial `d_filament` hole through all
  knuckles.
- `d_filament` default 1.9 (not 1.75): FDM holes print undersized, so 1.9 nominal
  gives a slip fit over a 1.75 mm strand. `clearance` is the axial gap between
  adjacent knuckles and MUST exceed one layer height so the print-in-place knuckles do
  not fuse.
- Taxonomy: `motion=hinge`, `reversible=true` (pull the filament strand to separate),
  `carries=["shear-xy"]`. Interface: `hinge_axis` along `+Y` (existing type).
- Orientation note in `use`: print flat, knuckle axis (Y) in the build plane so the
  bore prints as a clean horizontal bridge and the knuckle undersides self-support.

**`living_hinge` is a two-panel body joined by a single thin continuous web.**
Two rectangular panels of thickness `panel_t`, each `panel_w` wide (X), separated by
the hinge zone and bridged by a web of thickness `web_t` over width `web_w`, running
the full `length` (Y, the fold axis). The web is placed flush with one panel face
(default the +Z/top face) so the panels fold away from the web side.

- Signature: `living_hinge(length, panel_w, panel_t, web_t=0.6, web_w=2.0)`.
- `web_t` default 0.6 mm (a few FDM layers): thin enough to flex, thick enough to
  survive. `web_w` is the un-supported span that distributes the bend radius.
- Taxonomy: `motion=hinge`, `reversible=false` (one continuous piece; separating
  destroys it). `carries=["shear-xy"]` (tension along the fold; weak out-of-plane).
  Interface: `hinge_axis` along `+Y` (existing type; a flexure still folds about an
  axis).
- The `use` string MUST state the print orientation (flat, fold axis in the build
  plane, web continuous along Y so filament paths cross the bend) and the material
  caveat (PP/PETG/TPU flex repeatedly; PLA is brittle and cracks after few cycles).

**`shadow_gap` is an additive L-section lip on the front (visible) member.**
Seam plane at Y=0; the visible front member occupies Y<0 and the back member Y>0. Left
as a raw butt, the seam shows an irregular, tolerance-driven gap. The shadow gap fixes
this by stepping the back member back by `reveal` (~1 mm) so its visible face sits at
Y=`reveal`, producing a uniform recessed shadow line, while a return wall on the front
member projects to Y=`overlap` behind the back member to conceal the real interface.

- Signature: `shadow_gap(length, wall, overlap=3.0)`.
- Returns only the return-lip solid to `union` onto the inner face of the front
  member's edge: a bar of `length` (X) by `overlap` (Y) by `wall` thickness (Z),
  projecting from the seam plane Y=0 to Y=`overlap`. The visible front face is the
  existing panel and is unchanged; the reveal appears because the back member is
  shortened when placed.
- A single additive block (not a pair): the deliberate reveal and the back-member
  clearance are a placement relationship between two parts, not geometry this single
  lip can emit, so they are documented in the `use` string rather than carried as
  function parameters (`reveal`/`h`/`clearance` were dropped during implementation to
  avoid speculative, unused arguments).
- Taxonomy: `motion=rigid`, `reversible=true`, `carries=["lock-z"]` (the lip locks the
  back member against the visible face; it does not fasten on its own). Interface: new
  `seam` type along `+Y`.

**New interface type `seam`.** None of the existing closed-vocabulary types
(`face_mount`, `sliding_interface`, etc.) describe a concealed butt seam with a reveal.
Rather than overload `face_mount`, add `seam` to both the block-library closed
vocabulary and the `inventory_schema.json` interface `type` enum. Existing entries are
unaffected (additive enum change).

## Risks / Trade-offs

- **Living-hinge durability is material-dependent and outside the geometry.** Mitigated
  by encoding orientation + material guidance in the `use` string and `reversible=false`;
  the block does not promise a cycle count.
- **`d_filament` slip-fit default may vary by printer/filament tolerance.** Mitigated by
  exposing `d_filament` as a parameter and documenting the undersized-hole rationale.
- **`shadow_gap` correctness depends on manual placement of the shortened back member.**
  Mitigated by an explicit placement contract in the `use` string; matches how every
  other mate-pair block in the library is already placed.

## Migration

None. All three blocks are additive; no existing block, signature, schema field, or
inventory entry changes. The interface enum gains one value (`seam`); existing
inventory validates unchanged.
