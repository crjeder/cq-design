## Why

A block's `interfaces` array describes its physical connection points, but the closed
type vocabulary has no way to mark **where a block is rigidly fused into its parent part's
body**. The existing types split into two families: mating/assembly docks (`face_mount`,
`snap_hook`, `dovetail`/`finger`/`mortise`/`tenon`, ...) that join two **separately printed**
parts, and kinematic axes (`hinge_axis`, `axis`, `ball`, ...) that define a moving joint.
Neither expresses "this block is boolean-unioned into the same rigid body" -- e.g. a
`screw_boss` welded onto an enclosure wall, or a rib fused to a panel.

Without a `union` interface type, the planner cannot tell a fused sub-feature from a dock
that mates to a different printed part, and the tooling we want to build on top of
interfaces -- deriving union membership and world joint axes from the block descriptors
(the adjacent TODO item) -- has no signal for "fused, not mated." The TODO also notes
`hinge_axis` is "too narrow"; that generalization is separate, but the missing `union`
type is the concrete gap blocking the membership-derivation work.

## What Changes

- **Add `union` to the closed interface-type vocabulary.** A `union` interface marks a
  face or region where the block is rigidly fused (boolean-unioned) into its parent part's
  body, as distinct from a dock that mates with a separately printed part or a kinematic
  axis. The new type is accepted by the inventory schema enum and the inventory validator.
- **Document the semantic distinction.** The schema `type` description and the planning
  guidance SHALL explain when to use `union` (fused into the same rigid body) versus a
  mating dock (`face_mount` et al., two separate printed parts) versus a kinematic axis,
  so blocks and plans pick the right type.
- **Reconcile the spec's listed vocabulary with the implementation.** The `block-library`
  spec's "closed set" requirement currently lists only a subset and omits already-shipped
  types (`hinge_axis`, `ball`, `ball_socket`, `finger`, `mortise`, `tenon`, `dowel`); the
  modified requirement SHALL list the full current vocabulary plus `union`, so the spec
  matches the schema and validator.

## Impact

- Specs: `block-library` (modified) -- the interface-type-vocabulary requirement gains
  `union`, a `union`-accepted scenario, and a requirement describing its fused-to-body
  semantics.
- Tooling: `src/blocks/inventory_schema.json` (add `union` to the `type` enum + clarify the
  `type` description), `src/blocks/validate.py` (`_VALID_INTERFACE_TYPES` gains `union`).
- Guidance: `prompts/planning.md` -- a short note on choosing `union` vs mating-dock vs
  kinematic-axis interface types.
- Tests: `tests/test_blocks.py` -- a block descriptor declaring `"type": "union"` validates,
  and the shipped `inventory.json` still validates.
- Out of scope: generalizing or renaming `hinge_axis`; any planner/exporter logic that
  *consumes* `union` to auto-derive union membership or world joint axes (a later change);
  adding `union` interfaces to existing inventory blocks (vocabulary first, authoring later).
