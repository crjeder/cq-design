# Design: pin-hinge-member-unions

## Context

`pin_hinge` (`src/blocks/joints.py`) already builds two leaves as **geometrically disjoint** solids
(interleaved knuckles deliberately do not fuse) and then `union`s them into one `result` before
cutting the shared bore. `model_export` `makeCompound`s a part's `result` into one union, so the two
leaves arrive at the kinematic check as a single frozen body. The shipped multi-union machinery
(`units.resolve_unions`) already supports a part whose script returns a `dict[str, Workplane]` mapping
declared union ids to bodies -- `pin_hinge` just never used it.

`hinge_leaf` is a separate lone-half factory (one leaf per call, `side`/`variant` args) that the
`hinge-joint` capability is built around. It is the only current path to a two-separately-printed-part
hinge.

## Goals / Non-Goals

**Goals:**
- Make `pin_hinge` emit its two leaves as named member unions so a print-in-place hinge's own motion
  is kinematically checkable (leaf_a vs leaf_b).
- Retire the lone-half `hinge_leaf` matched-pair anti-pattern.
- Keep the pin-hinge spec honest (correct the stale dof example).

**Non-Goals:**
- Cross-part member distribution (leaf_a → door, leaf_b → wall), the `union` interface fuse pad,
  `parameters.py`, dovetail/ball merges, and the kinematic tree. All deferred to the tree slice.
- Any change to the hinge *geometry* -- only the return shape changes.

## Decisions

### D1: return `{"leaf_a", "leaf_b"}`, cut the bore from each

`pin_hinge` builds `part_a` (side-A leaf + its knuckles) and `part_b` (side-B leaf + its knuckles)
separately -- it already loops over the two sides -- then, instead of `result = A ∪ B`, cuts the
shared coaxial `bore` from each and returns `{"leaf_a": part_a.cut(bore), "leaf_b": part_b.cut(bore)}`.
Both leaves share the same bore axis, so each is bored identically; the pin passes through both. The
geometry of each leaf is byte-identical to what it is inside today's fused body.

### D2: union-id convention -- block keys are generic; the plan owns unique ids

The block returns the fixed keys `leaf_a`/`leaf_b`. A part using one `pin_hinge` declares
`unions: [{"id": "leaf_a"}, {"id": "leaf_b"}]` and its script returns the dict directly;
`resolve_unions` checks the keys equal the declared union ids. Because union ids are unique **across
the model**, a part that instantiates more than one hinge remaps in-script
(`result = {"lid_hinge_a": h["leaf_a"], ...}`) to keep ids unique. This is the existing multi-union
contract; `pin_hinge` needs no new machinery. The inventory `use` string documents the two-union
return so the planner declares the `unions`.

*Alternative considered:* have `pin_hinge` take a `name_prefix` param and bake unique keys. Rejected
-- it duplicates the plan's union namespace inside the block; the plan already owns union ids.

### D3: retire `hinge_leaf` wholesale; document the gap

`hinge_leaf`, its `blocks` re-export, and its inventory entry are removed, and the `hinge-joint`
capability with them. The separate-parts hinge it enabled is a genuine capability loss until the tree
can distribute `pin_hinge`'s members cross-part; this is stated as BREAKING with the migration being
"print-in-place -> `pin_hinge`; separate-parts -> returns with the tree." Retiring now (rather than
in the tree slice) removes the drift-prone footgun immediately, per the `joint-contract` D3 decision.

### D4: correct the stale dof example in the pin-hinge spec

The `single-axis-joint-contract` change reshaped `dof` to the vector model but did not update the
`pin-hinge` spec's example (`{type: revolute, axis: Y, mechanical_limit, unit}`). Since this change
rewrites that requirement anyway, the example is corrected to `{type: revolute, direction: [0,1,0],
origin: [0,0,0], mechanical_limit: [0,180]}` (unit derived), matching `inventory.json` on `main`.

## Risks / Trade-offs

- **Separate-parts hinge capability gap.** -> Documented BREAKING; the common (print-in-place) case is
  unaffected, and the capability returns with the tree. Accepted per the scope decision.
- **A `pin_hinge` part must now declare two `unions`.** -> The inventory `use` string states this; a
  planning-prompt note reinforces it. A part that forgets gets a `resolve_unions` mismatch error (the
  existing well-formedness check), not a silent fusion.
- **Existing plans/scripts that used the fused `pin_hinge` Workplane break.** -> There are none in the
  repo today (verified); the block is only exercised by tests, which this change updates.

## Migration Plan

1. Split `pin_hinge`'s return; delete `hinge_leaf` + its re-export.
2. Update `inventory.json` (pin_hinge `use`/unions note; remove `hinge_leaf`).
3. Update `prompts/planning.md`.
4. Update tests (block return shape; add the leaf-vs-leaf kinematic sweep; drop `hinge_leaf` tests).

Rollback = revert; validation/geometry only, no persisted artifacts.

## Open Questions

- Whether the inventory descriptor should gain a structured `unions: ["leaf_a","leaf_b"]` field or
  just document the two-union return in `use`. Lean: document in `use` for this slice (a structured
  block->unions field is better designed alongside the tree). Decide during implementation.
