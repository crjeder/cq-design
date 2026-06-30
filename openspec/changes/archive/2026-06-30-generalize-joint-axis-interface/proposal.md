## Why

The block interface vocabulary names a revolute joint's axis `hinge_axis`, but "where the
joint's degree of freedom acts" is motion-agnostic: a prismatic joint has a slide axis and a
spherical joint a pivot center, the same kind of reference. `hinge_axis` bakes "hinge" into a
concept that applies to all three motion types, so the kinematic-axis vocabulary is narrower
than the `dof.type` vocabulary (`revolute`/`prismatic`/`spherical`) it should mirror. The
interface `type` is descriptive metadata -- no runtime code consumes it beyond vocabulary
validation -- but it drives planner reasoning and is mandated by the `living-hinge`,
`pin-hinge`, and `joint-classification` specs, so a hinge-only token misleads anyone
authoring a non-revolute joint.

This is the companion to the just-added `union` interface type: together they make the
interface vocabulary express all three relationship families cleanly (fused / mating dock /
kinematic axis), with the kinematic family no longer hard-wired to hinges.

## What Changes

- **Replace `hinge_axis` with a motion-agnostic `joint_axis` type.** `joint_axis` marks a
  block's kinematic reference: the rotation axis (revolute), translation axis (prismatic), or
  pivot center (spherical) of the joint the block forms. The specific motion kind is read from
  the block's `dof.type`; a dof-less flexure (`living_hinge`) uses `joint_axis` for its bend
  axis with no `dof`.
- **Migrate the three blocks that use `hinge_axis`** (`hinge_leaf`, `pin_hinge`,
  `living_hinge`) to `joint_axis`, and **retire `hinge_axis`** from the vocabulary (the schema
  enum and the validator set). No other block uses it, and interface types appear only in
  `inventory.json` (which we control), so the rename is safe and complete.
- **Keep the geometry-dock and feature-axis tokens as-is.** `ball`/`ball_socket` and
  `sliding_interface` describe mating geometry (a socket cups a ball; a groove captures a
  tongue), and `axis` is a non-kinematic bore/feature axis; none is the joint-DOF reference,
  so none is renamed.
- **Update guidance and the mandating specs.** `prompts/planning.md` and the `block-library`,
  `joint-classification`, `living-hinge`, and `pin-hinge` specs SHALL refer to `joint_axis`
  instead of `hinge_axis`.

## Capabilities

### Modified Capabilities
- `block-library`: the closed interface-type vocabulary drops `hinge_axis` and gains
  `joint_axis`, plus a requirement defining `joint_axis` as the motion-agnostic kinematic-axis
  reference.
- `joint-classification`: the taxonomy's mandated interface-type set refers to `joint_axis`.
- `living-hinge`: the living hinge declares a `joint_axis` interface.
- `pin-hinge`: the pin hinge declares a `joint_axis` interface.

## Impact

- **Stacking:** this change edits the `block-library` "closed set" and `union` requirements
  that the `add-union-interface-type` change (PR #13) introduced, so it SHALL be applied on
  top of that change (branch off it, or off `main` once #13 merges).
- Tooling: `src/blocks/inventory_schema.json` (enum + `type` description), `src/blocks/validate.py`
  (`_VALID_INTERFACE_TYPES`), `src/blocks/inventory.json` (3 blocks: `hinge_leaf`, `pin_hinge`,
  `living_hinge`).
- Guidance: `prompts/planning.md`.
- Tests: `tests/test_blocks.py` -- `joint_axis` validates, the retired `hinge_axis` is rejected,
  the shipped inventory still validates and declares no `hinge_axis`.
- Out of scope: migrating `dovetail`/`ball` blocks to `joint_axis` (they keep their mating-geometry
  tokens); any new code that *consumes* `joint_axis` (none exists today).
