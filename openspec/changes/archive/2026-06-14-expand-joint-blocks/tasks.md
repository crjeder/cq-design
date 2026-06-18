## 1. Schema and taxonomy

- [x] 1.1 Extend `blocks/inventory_schema.json`: add optional item properties `motion`
  (enum `rigid|hinge|ball`), `reversible` (boolean), `carries` (array of string)
- [x] 1.2 Extend the interface `type` enum with `hinge_axis`, `ball`, `ball_socket`,
  `finger`, `mortise`, `tenon`, `dowel`
- [x] 1.3 Confirm existing `blocks/inventory.json` still validates (run `blocks/validate.py`)
- [x] 1.4 Annotate the two existing dovetail entries with `motion: rigid`,
  `reversible: true`, `carries: ["shear-xy", "lock-z"]`

## 2. Shared construction cores

- [x] 2.1 Add private extrude-profile helpers to `blocks/joints.py`: build a 2D
  section (trapezoid / square), extrude along the mate axis, optional tile along an
  edge, with a single `clearance` fit term and a positive/negative role
- [x] 2.2 Refactor `dovetail_groove`/`dovetail_tongue` onto the extrude core with no
  signature or geometry change (existing tests must still pass)
- [x] 2.3 Add private revolve helper (sphere/cylinder of revolution) and tiled-cylinder
  helper (alternating knuckles on an axis)

## 3. Finger joint (extrude core)

- [x] 3.1 Implement `finger_joint(width, thickness, fingers, length, clearance=0.1, start_high=True)`
  - alternating rectangular fingers across `width`, height `thickness`, depth `length`
- [x] 3.2 `start_high` selects the complementary comb so two calls interlock
- [x] 3.3 `clearance` shrinks each finger by `clearance` per side in the tiling axis
- [x] 3.4 Inventory entry: `motion: rigid`, `reversible: true`, `carries: ["shear-xy"]`,
  `finger` interface

## 4. Mortise and tenon (extrude core)

- [x] 4.1 Implement `tenon(w, h, length, clearance=0.0)` - rectangular peg
- [x] 4.2 Implement `mortise(w, h, depth, clearance=0.2)` - rectangular pocket to subtract,
  grown by `clearance` per side
- [x] 4.3 Inventory entries with `tenon` / `mortise` interfaces; `motion: rigid`,
  `reversible: true` (tenon), `carries: ["shear-xy", "lock-xy"]`

## 5. Dowel pin and bore (revolve core)

- [x] 5.1 Implement `dowel_pin(d, length, chamfer=0.4)` - cylinder with lead-in chamfer
- [x] 5.2 Implement `dowel_bore(d, depth, clearance=0.1)` - bore to subtract; negative
  `clearance` documents the press-fit (interference) regime
- [x] 5.3 Inventory entries with `dowel` interface; `reversible: false` default (press),
  note clearance flips it; `carries: ["shear-xy"]`

## 6. Ball joint (revolve core)

- [x] 6.1 Implement `ball_stud(d_ball, d_stem, stem_l, fillet=...)` - sphere on a stem
  with stem->ball fillet for printability
- [x] 6.2 Implement `ball_socket(d_ball, retention_angle, slot_w, wall, clearance=0.2)`
  - slotted cup capturing the ball past its equator
- [x] 6.3 Inventory entries with `ball` / `ball_socket` interfaces; `motion: ball`,
  `reversible: true` (snap-in)

## 7. Hinge (tiled-cylinder core)

- [x] 7.1 Implement `hinge_leaf(length, knuckles, d_outer, d_pin, leaf_w, leaf_t, clearance=0.3, side="A", variant="pin")`
- [x] 7.2 `side` A/B interleaves knuckles so two leaves mesh; `variant` selects bored
  pin hole (`pin`) vs printed-in-place gap (`print_in_place`)
- [x] 7.3 Inventory entry with `hinge_axis` interface; `motion: hinge`,
  `reversible: false` (pinned); `use:` string states required print axis
- [x] 7.4 Document print-in-place clearance and orientation in the `use:` string

## 8. Exports and validation

- [x] 8.1 Export all new functions from `blocks/__init__.py` and update its `__all__`
- [x] 8.2 Validate `blocks/inventory.json` against the updated schema
- [x] 8.3 `ruff check --fix` and `ruff format` on `blocks/joints.py` and `__init__.py`

## 9. Tests

- [x] 9.1 `tests/test_blocks.py`: per pair, assert bounding box, X/axis symmetry, and
  the clearance relationship (negative member larger than positive by `2*clearance`)
- [x] 9.2 Finger joint: two complementary combs occupy disjoint X bands with the
  expected gap; union spans full `width`
- [x] 9.3 Ball socket: opening diameter < ball diameter (retention); slot present
- [x] 9.4 Hinge: two leaves' knuckles interleave without overlap at `clearance`
- [x] 9.5 Confirm existing dovetail tests still pass after the core refactor

## 10. Verify (printed coupons)

- [x] 10.1 Export STL for each pair; run `preview.py` to confirm orientation/cross-section
  (STLs exported to `build/joint_verify/`; multi-view previews confirm ball-stud
  fillet and hinge knuckle interleave/bore)
- [x] 10.2 Printability checked via trimesh overhang analysis (orca-check MCP not
  connected this session; same method scad-analyzer uses). In intended print
  orientation: finger_joint, tenon, dowel_pin, ball_stud, ball_socket all 0% overhang
  (self-supporting) — the ball_stud cone fillet keeps the exposed underside at ~53deg
  and the 30deg ball_socket retention keeps the lip at ~60deg. hinge_leaf flags under a
  strict 45deg metric (horizontal pin bore bridge + convex knuckle lower quadrants);
  both bridge/self-support in a real slicer at d_pin~3mm. inventory `use` corrected to
  state this honestly. A true OrcaSlicer pass on the hinge remains advisable.
- [ ] 10.3 Tune default `clearance` per mechanism from a printed fit-test coupon
  — BLOCKED: requires a physical print
