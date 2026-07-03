## Why

A matched-pair block (`pin_hinge`) already emits both members of a joint from one call, but
`BUILD_PLAN.json` has no way to say which part each member fuses into, or to compute one mated
part's assembled pose from the other's. Every part -- even one whose whole position is dictated by
a hinge it shares with another part -- still needs its own hand-authored, independently-computed
`placement`, and nothing catches a part left unreachable from the assembly's anchor or given two
conflicting anchors. This is the "buildable core" of Slice B named in the archived
`openspec/changes/archive/2026-07-01-joint-contract` design (D6/D6b): a plan-level `joint` entity
that names a matched pair's block, its two members, and which part each fuses into, so a mated
part's pose can be *derived* along the mate chain instead of hand-computed.

## What Changes

- Add optional `joints` (array) and `root_part` (string) fields to `BUILD_PLAN.json`. Each `joint`
  entry names a matched-pair block and its two `members`: `{member, part, dock}`, where `member` is
  the key the block's returned `dict[str, Workplane]` uses for that body, `part` is the id of the
  part whose script fuses it in, and `dock` reuses the existing `placement` shape (ordered
  rotate + translate) but means the member's pose **within its host part's own authored frame**
  (not the assembled frame).
- Add an `emits` field to a matched-pair block's inventory descriptor (`blocks/inventory.json`,
  alongside the existing `dof`; documented under `joint-mate-entity` the same way `dof` is
  documented under `kinematic-range-validation` rather than under the generic `block-library`
  inventory-schema capability): the block's member ids (e.g. `["leaf_a", "leaf_b"]`), so a `joint`
  entry's declared member ids can be cross-checked mesh-free instead of only failing at
  part-script-run time.
- `plan_validate.py`: cross-check each `joint`'s `members` against declared parts/unions and the
  block's `emits`, and validate the mate graph -- every part is reachable from `root_part` along
  exactly one path through `joints` (or has none), catching an **unanchored** part (no `placement`,
  no path from the root) or a **double-anchored** part (reachable via the mate chain but also
  declaring its own `placement`, an ambiguous conflict).
- A new pose-derivation helper computes a mated part's assembled-frame transform by composing the
  mate chain from `root_part`: for a joint linking member A (on a part with known world pose) and
  member B (on the part to derive), `world_pose(part_B) = world_pose(part_A) . dock_A . inverse(dock_B)`
  -- both members are already mutually consistent in the block's own shared local frame, so this
  composition is exact, not solved for. `model_export.py` uses the derived transform in place of a
  part's own `placement` for any part reached via the mate chain.

Out of scope (explicitly deferred, cross-referenced as follow-ups to the same Slice B, per the
archived design):
- **`parameters.py` generation.** D6's "drift is impossible by construction" guarantee -- a
  generated file both member scripts import so their block calls are machine-guaranteed to share
  literal params -- is not built here. This change lets the plan describe and derive poses from an
  already-matched pair; it does not yet enforce that both scripts' block calls used identical
  params. Today's status quo (an author keeping two calls in sync by hand) is unchanged for now.
- **Deriving `kinematics` entries from a `joint`.** The hand-written `kinematics` array (shipped,
  and extended by `recursive-kinematics-tree`) remains the only form; auto-deriving an entry from a
  `joint`'s block dof + derived axis is a later step once this lands.
- **Mate-area / keep-out geometry** (Slice C) -- unrelated, independent.
- **Merging dovetail/ball into matched-pair blocks.** Only `pin_hinge` exists as a matched-pair
  block today; this change works with whatever matched-pair blocks exist. Dovetail/ball stay
  lone-half blocks until a separate change merges them (per D3, not required for this one).
- **Auto face-normal-driven dock seating.** `dock` is an author-supplied rotate/translate transform
  (same shape as `placement`), not solved from a named surface -- the richer "which surface, where
  on it" mate-area model is future work.

## Capabilities

### New Capabilities
- `joint-mate-entity`: the plan-level `joint` entity (matched-pair block, `params`, two `members`
  each with a `dock`), the `root_part` anchor, the pose-derivation composition along the mate
  chain, and the block-descriptor `emits` field the entity validates against.

### Modified Capabilities
- `assembly-phase`: a part reached via the mate chain gets its assembled pose *derived* from its
  joint's dock transforms and its mate-chain ancestor's pose, instead of requiring its own
  hand-authored `placement`; a part with neither `placement` nor a mate-chain path is invalid.

## Impact

- `src/build_plan_schema.json` -- add `joints`, `root_part`; the `joint` entry's `dock` reuses the
  existing `placement` definition (also promoted to `definitions` for the `$ref`, mirroring
  `recursive-kinematics-tree`'s `kinematics_entry` pattern).
- `src/blocks/inventory_schema.json` and `src/blocks/inventory.json` -- add `emits` to matched-pair
  block descriptors (`pin_hinge` gets `["leaf_a", "leaf_b"]`).
- `src/plan_validate.py` -- new `_check_joints`: member/part/block cross-checks, `emits` match, mate
  graph reachability (unanchored/double-anchored detection).
- New small module (e.g. `src/mate_chain.py`) -- composes the mate chain from `root_part`, producing
  a 4x4 transform per mated part, reusing `placement.py`'s matrix helpers.
- `src/model_export.py` -- use the derived transform for a mate-chain part instead of requiring its
  own `placement`.
- `openspec/specs/assembly-phase/spec.md` -- delta for the derived-pose behavior.
- Existing plans with no `joints`/`root_part` are unaffected (every part keeps using its own
  authored `placement`, identity when absent, exactly as today).
