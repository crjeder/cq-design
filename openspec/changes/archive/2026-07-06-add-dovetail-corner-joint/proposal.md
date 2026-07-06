## Why

The skill's only dovetail block today (`dovetail_groove`/`dovetail_tongue`) is a *sliding rail*
dovetail for a lid sliding into a box top edge -- it has no analog for the classic multi-pin
*corner box joint* (drawer front-to-side style: alternating trapezoidal pins and tails tiled
across a board end, assembled by pressing straight together, not sliding). A user supplied a
public-domain OpenSCAD implementation of exactly that joint
(`dovetail_pins`/`dovetail_tails`/`dovetail_pins_idealized` + board-assembly helpers) and asked
for a ported block version, with three concrete gaps in the reference fixed: it has no fit
tolerance at all (pins and tail sockets are cut from the literal same idealized geometry, a
theoretical zero-clearance fit), it hardcodes a 90-degree corner (`rotate([-90, 0, 0])`, i.e. the
two boards must be exactly perpendicular), and it has no formal mating contract a downstream
tool could check (it's a standalone `.scad` file, not part of a block system with a planner and
a validator).

## What Changes

- New `dovetail_corner_joint` block in `blocks/joints.py` (module `blocks.joints`), a CadQuery
  port of the referenced multi-pin dovetail box joint. Returns
  `{"pins": Workplane, "tails": Workplane}` in one shared local frame (mirroring `pin_hinge`'s
  existing matched-pair dict convention), derived from one internal idealized-comb helper so the
  two halves stay geometrically complementary by construction -- the same trick the reference
  uses via `intersection()`/`difference()`.
- Adds a `clearance` parameter (absent in the reference): a per-side mating gap between the
  pins and tail sockets, following this codebase's existing sign convention (positive =
  separable gap fit, negative = interference/press fit; see `dovetail_tongue`, `mortise`,
  `finger_joint`).
- Replaces the reference's hardcoded `rotate([-90, 0, 0])` with a `corner_angle_deg` parameter
  (default 90, matching the reference's assumed right-angle corner) so the two boards can meet at
  any dihedral angle, not only a perpendicular corner.
- Declares a real mating contract: `emits: ["pins", "tails"]` in `blocks/inventory.json`, so the
  block can back a `joints` entry through the existing cross-part matched-pair mechanism (two
  different boards -- e.g. a drawer front part and a drawer side part -- each pull their own
  member out of the returned dict and cut/union it into their own body, with the relative pose
  reconciled via each member's own `dock`). This is the "two different parts" case the
  `joint-mate-entity` spec already generalizes; no new schema mechanism is needed, only a new
  block that uses it.
- Adds a new `dovetail_corner` interface type to the closed interface-type vocabulary (distinct
  from the existing `sliding_interface` type used by the rail dovetail), enforced identically by
  `inventory_schema.json` and `blocks/validate.py` per the existing `block-library` contract.
- Integrates the block for both planner and part-designer use by following the same
  self-documenting convention `pin_hinge` already established: the inventory `use` text spells
  out the `emits` dict-key contract in prose (which member each board pulls, when to author a
  `joints` entry vs. this block's `unions` alternative for a monolithic single-part case) so no
  changes to `prompts/planning.md`'s or `prompts/part.md`'s generic rules are needed -- rule 7
  (matched-pair block across two different parts) already covers the mechanism generically.

## Capabilities

### New Capabilities
- `dovetail-corner-joint`: parametric multi-pin dovetail corner (box) joint block --
  `dovetail_corner_joint` CadQuery factory, its tolerance/clearance behavior, its
  `corner_angle_deg` generalization of the reference's fixed 90-degree assumption, and its
  matched-pair mating contract (`emits`, inventory entry, interface type).

### Modified Capabilities
- `block-library`: the closed interface-type vocabulary gains `dovetail_corner`, enforced
  identically by the JSON Schema enum and `blocks/validate.py`'s validator, per the existing
  "Interface type vocabulary is a closed set" requirement.

## Impact

- `src/blocks/joints.py` -- new `dovetail_corner_joint` function (plus an internal
  idealized-comb helper, not exported).
- `src/blocks/inventory.json` -- one new entry (`dovetail_corner_joint`, `emits`, `motion:
  rigid`, `reversible: true`, `carries`, one `dovetail_corner` interface).
- `src/blocks/inventory_schema.json` -- add `dovetail_corner` to the interface `type` enum.
- `src/blocks/validate.py` -- add `dovetail_corner` to `_VALID_INTERFACE_TYPES`.
- No changes to `plan_validate.py`, `mate_chain.py`, `model_export.py`, or the `joints`/`emits`
  schema machinery -- all already generic per `joint-mate-entity`.
- No changes to `prompts/planning.md` or `prompts/part.md` -- existing generic rules and the
  inventory `use`-text convention already cover a new matched-pair block.
- New tests in `tests/test_blocks.py` (geometry, clearance sign, angle generalization) and
  `tests/test_plan_validate.py`/`tests/test_mate_chain.py` style coverage confirming the new
  block validates correctly as a `joints` entry's `block`.
