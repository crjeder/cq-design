## Context

`blocks/joints.py` already has one dovetail pair (`dovetail_groove`/`dovetail_tongue`, a sliding
rail dovetail for a lid-into-box slot) and one multi-tooth interlocking pair
(`finger_joint`, rectangular teeth, called twice with opposite `start_high`). Neither is the
classic woodworking corner box joint the user supplied a reference OpenSCAD implementation of:
alternating trapezoidal pins and tails tiled across a board's end, joining two boards at a
corner. That reference (`dovetail_pins`/`dovetail_tails`/`dovetail_pins_idealized`) derives both
interlocking halves from one shared "idealized comb" module via `intersection()` (keep, for the
pin board) and `difference()` after a hardcoded `rotate([-90, 0, 0])` (cut, for the tail board) --
a clean trick for guaranteeing the two halves stay complementary, but with three gaps: no fit
tolerance (pins and sockets are the literal same geometry, a theoretical zero-clearance fit), a
fixed 90-degree corner assumption baked into the rotate, and no formal mating contract (it's a
bare `.scad` file, not integrated with a planner or a validator).

This project already has a generic mechanism for exactly this shape of problem: a "matched-pair
block" declares `emits: [id_a, id_b]` in `blocks/inventory.json`; its function returns
`dict[str, Workplane]`; a `BUILD_PLAN.json` `joints` entry wires each member to its own part with
a `dock` transform, and `mate_chain.py` derives the assembled poses (see `joint-mate-entity`
spec). `pin_hinge` is the one shipped example, but for the same-part `unions` case (both leaves
in one printed part). A corner box joint is the same matched-pair shape but for the *cross-part*
case (two different, otherwise-unrelated boards) -- the "door leaf and a wall leaf" example
`planning-phase` rule 7 already names generically but that no shipped block yet exercises.

## Goals / Non-Goals

**Goals:**
- Port the reference's pin/tail comb generation to CadQuery as one matched-pair block,
  `dovetail_corner_joint`, returning `{"pins": Workplane, "tails": Workplane}`.
- Add a real `clearance` parameter (the reference has none).
- Replace the hardcoded `rotate([-90, 0, 0])` with a `corner_angle_deg` parameter so the two
  boards can meet at any dihedral angle, not only a right angle.
- Give the block a real mating contract: `emits`, a new closed-vocabulary interface type, and an
  inventory `use` string that documents the dict-key contract in the same self-documenting style
  `pin_hinge` already established, so no prompt-template changes are needed for the planner or
  the part designer to use it correctly.

**Non-Goals:**
- Generating the boards themselves. Like every other block in `blocks/joints.py`
  (`dovetail_groove`, `mortise`, `finger_joint`), this block generates only the joint *feature*
  (the comb to union or the sockets to cut); the caller's part script authors the actual board
  body and unions/cuts this block's output onto it.
- Correctly mitering the board bodies for a non-90-degree corner so their faces meet flush. That
  is the caller's board geometry, not this block's -- `corner_angle_deg` only controls the
  relative angle baked into the tooth-cutting geometry itself (see Decisions).
- Reproducing the reference's `board_with_dovetail_pins`/`board_with_dovetail_tails` whole-board
  demo modules. Out of scope for the same reason `dovetail_groove` doesn't generate a whole box.
- Supporting different thickness for the two boards. The reference's own top-level example also
  assumes one shared thickness; a differing-thickness variant is a later extension if needed.
- Any change to `plan_validate.py`, `mate_chain.py`, `model_export.py`, the `joints`/`emits`
  schema, or `prompts/*.md` -- all already generic per `joint-mate-entity` and `planning-phase`
  rule 7.

## Decisions

- **One matched-pair function, not two independent ones.** The reference's `dovetail_pins` and
  `dovetail_tails` are two separate OpenSCAD modules that both happen to reference the same
  idealized comb. Exposing that as two independently callable inventory blocks would let a caller
  invoke just one half with mismatched parameters, silently breaking the complementary-geometry
  guarantee. `pin_hinge` already established the alternative: one function, one call, a dict of
  both members, declared via `emits` -- callers pull out their own key. Same choice here.

- **`pins` is a union feature, `tails` is a cut feature -- not two cut/union-agnostic blobs.**
  Mirroring `dovetail_groove` (cut) and `finger_joint`'s combs (union): `pins` is the positive
  comb the pin-board part unions onto its own end face; `tails` is the socket-shaped cutting tool
  the tail-board part `.cut()`s from its own end face. The reference's `dovetail_tails` actually
  manufactures a whole slab-with-sockets-already-cut, which doesn't fit this codebase's
  feature-only block convention -- rejected in favor of returning just the cutting tool, same as
  `mortise`.

- **Reuse `_trapezoid_profile`/`_extrude_profile` for the per-tooth cross-section, tile like
  `finger_joint`.** The reference's per-tooth polygon (`pin_width` at the base narrowing to
  `pin_width_top` over `pin_thickness`) is exactly the trapezoid `_trapezoid_profile` already
  builds for `dovetail_groove`/`dovetail_tongue` (`half_base` at Z=0, `half_top` at Z=depth). A
  new `flare_deg` parameter (per-tooth taper angle from the tooth's straight side, default 15 to
  match the reference; 0 = rectangular finger, larger = more undercut) computes
  `half_top = half_base - tan(radians(flare_deg)) * board_thickness`, then `pin_count` copies are
  tiled across X at `pitch = pin_width + tail_width` and unioned, following `finger_joint`'s own
  loop-and-union pattern and its X-centering convention (`x_center = -total_width/2 + (i+0.5) *
  pitch`).

  **Naming note:** `flare_deg` is deliberately a new, distinctly-named parameter, not reusing
  `dovetail_groove`/`dovetail_tongue`'s existing `angle` (measured from vertical, opposite
  convention -- larger there means *shallower*/more printable, larger here means *more* flare).
  Reusing the name across two different conventions in the same file would be a real footgun for
  the block-selecting LLM; the inventory `use` text calls this out explicitly.

- **Drop the reference's clipping-cube epsilon trick.** The `intersection()`/`difference()`
  against a `translate([0.005,...]) cube([...-0.01,...])` in the reference is an OpenSCAD/CGAL
  coincident-face manifold-safety trick, not load-bearing geometry -- it doesn't even appear to
  span the full tooth footprint exactly (its width term is one `pin_width` short of the true
  tooth-to-tooth span, which is immaterial to a render-safety clip but would matter if it were
  meant to be a real geometric bound). CadQuery/OCC booleans don't share that limitation, and
  neither `dovetail_groove` nor `finger_joint` need one. Each tooth's own trapezoid profile
  already exactly bounds its own footprint; no separate clip is needed.

- **`corner_angle_deg` replaces the fixed `rotate([-90, 0, 0])` with a rotation about the shared
  corner edge.** The tooth-tiling axis (X) is physically the corner edge line shared by both
  boards regardless of the angle between their faces. In the reference, `pins` lives in its
  natural frame (comb axis = Y protrusion/insertion, taper axis = Z board-thickness); `tails`
  needs the *same* comb rotated so its Y (protrusion/insertion) becomes the tail board's own
  through-thickness axis -- a swap that, for a perpendicular corner, is exactly a 90-degree
  rotation about the shared X edge. Generalizing: `tails = pins_comb.rotate(about the X axis
  through the corner edge, by -corner_angle_deg)`, default 90 to match the reference exactly (at
  `corner_angle_deg=90` this is bit-identical to the reference's hardcoded rotate). This is a
  well-defined, exact generalization *for the tooth/socket feature itself* -- it does not attempt
  to also miter the surrounding board bodies to meet flush at the new angle (Non-Goals).

- **Clearance lives entirely on `tails` (the cutting tool), unchanged on `pins`.** Matches
  `mortise`'s convention (grows the subtractive cavity) rather than `dovetail_tongue`'s (shrinks
  the positive member) -- either is valid per `joint-classification`'s sign contract, but since
  `pins` here is the union feature and `tails` the cut feature, growing the cut side by
  `clearance` per side (both `half_top` and `half_base` of the tail socket profile grown by
  `clearance`) keeps `pins` at its nominal tiled dimensions and needs no extra parameter
  threading. Positive `clearance` (default 0.1, matching `finger_joint`/`dovetail_tongue`'s
  existing per-side defaults) grows the socket for a separable gap fit; negative shrinks it for
  an interference/press fit, per `joint-classification`'s existing sign convention.

- **New `dovetail_corner` interface type, not reusing `sliding_interface` or `finger`.** The
  existing `sliding_interface` type describes the *rail* dovetail's continuous slide-in mate,
  which is the wrong semantics here (assembly is a straight press-together across many teeth
  simultaneously, not a sliding traversal). `finger` already exists for the rectangular
  interlocking comb; reusing it for a *dovetail*-shaped comb would blur two visually and
  mechanically distinct joint families in the inventory. One new type, declared on both the
  `pins` and `tails` interface entries (mirroring `finger_joint`'s single shared type for both of
  its interlocking halves).

- **No `dof` field.** Like `finger_joint` (rigid, no kinematic axis), assembly is a one-shot press
  together across the whole comb, not a partial-range motion a `kinematics` entry would sweep.
  Declaring a `dof` would pull this block into `joint-contract`'s revolute/prismatic checking for
  no benefit; omitting it (as `finger_joint` already does) sidesteps that entirely.

## Risks / Trade-offs

- [`corner_angle_deg` only rotates the tooth/socket feature, not the board bodies] -> Acceptable
  and consistent with every other block in this file being feature-only; documented as an
  explicit Non-Goal and called out in the function's own docstring so a part-designer LLM knows
  it must shape its own board face at the matching angle.
- [Two distinct "angle" parameter conventions now exist in the same module
  (`dovetail_groove.angle` vs. `dovetail_corner_joint.flare_deg`/`corner_angle_deg`)] -> Mitigated
  by giving the new parameters distinct names and calling out the difference explicitly in both
  the docstring and the inventory `use` text, rather than reusing `angle`.
- [No shipped example yet exercises the cross-part `joints`/`dock` mechanism end to end] ->
  This change is also the first real integration test of that path; covered by new
  `tests/test_plan_validate.py`/`tests/test_mate_chain.py`-style coverage instantiating a `joints`
  entry with this block and confirming it validates and derives a pose, in addition to
  `tests/test_blocks.py` geometry coverage.
- [Dropping the reference's clipping-cube changes exact bounding-box numbers vs. the reference]
  -> Not a compatibility concern (this is a from-scratch CadQuery port, not a byte-for-byte port);
  covered by dedicated geometry tests against the new implementation's own documented formulas,
  not the reference's.
