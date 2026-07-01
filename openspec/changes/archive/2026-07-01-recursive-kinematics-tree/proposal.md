## Why

`kinematic_check.py` treats every joint as an isolated hinge on an otherwise rigid
model: sweeping a `moving_union` tests it against "every other union" as fixed. That
breaks down for a chain of joints (e.g. shoulder -> forearm -> hand): the forearm and
hand are rigidly carried by the shoulder, but today they're swept as fixed obstacles,
producing false-positive `motion_collision` findings against the shoulder's own
downstream links, and masking any real collision between the moving sub-assembly and
the rest of the model. There is currently no schema field that says which joint sits
downstream of which, so this can't even be expressed today.

This is a narrower, compatible slice of the tree unification already decided in
`openspec/changes/archive/2026-07-01-joint-contract` (D7: "Assembly structure is a
recursive kinematic tree," filed as "Slice B -- NEXT"). That decision unifies
`placement` and `joint` into one parent edge across the whole plan (parts become
tree nodes, not just kinematics entries) and bundles matched-pair joint blocks and
a plan-level `joint` entity. This change does not attempt any of that -- it only
nests the existing `kinematics` array on today's flat `parts`/`placement` schema,
to fix the sweep's false-positive/false-negative problem now. It reuses the same
resolved shape (nested `children`, parent owns the edge, tree-only/no closed
loops) so it composes with Slice B rather than conflicting with it.

## What Changes

- Add an optional `children` field to each `kinematics` entry: an array of nested
  `kinematics` entries mounted on this joint's `moving_union`. This turns the
  `kinematics` array from a flat list into a forest -- each top-level entry a root
  mounted on the static frame, each entry's `children` mounted on it in turn. The
  parent declares its children (never the reverse), so cycles are structurally
  impossible and there is nothing to walk back up.
- `plan_validate.py`: recurse into `children` at every depth and apply the existing
  per-entry checks (`moving_union` resolves to a union id, block/dof exist, joint
  contract) uniformly regardless of nesting depth.
- `kinematic_check.py`: for each entry's sweep (at any depth), the swept subtree is
  itself plus every entry nested under its `children`, collected by a plain
  recursive walk. Apply the same per-step transform to the whole subtree (rigid
  carry-along; descendant joints stay at their own authored zero during an
  ancestor's sweep), and derive the fixed collision set as every union NOT in that
  subtree -- instead of "every other union in the model."
- Update the `kinematic-range-validation` spec's schema and fixed-set requirements
  to reflect the nested tree and subtree-aware sweeping.

Out of scope: composing simultaneous multi-joint motion (sweeping two joints at
once) and rigid grouping of non-jointed unions (a plain union welded to a moving
union with no joint of its own). Both are natural follow-ups but not required to
fix the false-positive/false-negative problem described above.

## Capabilities

### Modified Capabilities
- `kinematic-range-validation`: the build-plan schema for a `kinematics` entry
  gains a recursive `children` field, turning the array into a forest; the sweep's
  fixed-set derivation becomes subtree-aware instead of "every other union."

## Impact

- `src/build_plan_schema.json` -- add a recursive `children` field to the
  `kinematics` entry schema (self-referencing via `$ref`/`definitions`).
- `src/plan_validate.py` -- `_check_kinematics` recurses into `children` and
  applies the existing per-entry checks at every depth.
- `src/kinematic_check.py` -- recursively collect each entry's subtree from its
  `children`, sweep the subtree as a rigid group, derive the fixed set as the
  complement.
- `openspec/specs/kinematic-range-validation/spec.md` -- delta for the changed
  fixed-set requirement and the new schema field.
- Existing plans with no `children` fields are unaffected (every entry is a root
  mounted on the static frame, i.e. today's behavior of one moving union vs.
  everything else).
