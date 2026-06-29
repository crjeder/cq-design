## Why

> **Status: exploratory capture, NOT ready to implement.** This records a design direction
> worked out in an explore session. Two cruxes are deliberately open (see Open Questions);
> `tasks.md` stays blocked until they resolve. Read `design.md` for the full model.

Today a joint is fragmented. A block's `dof` is an intrinsic, body-agnostic descriptor
(`{type, axis, mechanical_limit, unit}`); the plan's `kinematics` array separately names the
moving union and the assembled-frame axis; and `plan_validate` only checks `unit` -- it never
checks that the plan's joint `type` matches the block's `dof.type`, so a `revolute` joint
declared against a `ball_socket` block passes validation today. The block-library rule that
"each part is one rigid body" forces the two members of a joint (a hinge's two leaves) into two
independent parts, throwing away the fact that they are one joint with a known degree of freedom
and re-asserting it by hand in `kinematics`.

The reframe: **`dof` is a contract, not a property.** A joint is a relation between two unions
`A` and `B`; the PLAN states the *wish* ("what the model needs") and the BLOCK states the
*reality* ("what the LEGO piece provides") in the *same* vocabulary; a joint is satisfied when
reality covers the wish. This makes joint incompatibility obvious (you cannot satisfy a hinge
wish with a ball-socket block), lets one block own both members of a joint (emitting two unions),
and -- with that -- lets the kinematics be *derived* rather than hand-written, which is the
foundation for articulated chains.

## What Changes (direction, not yet committed)

- **Joints become relational contracts.** A joint relates two unions `A`/`B` (symmetric -- the
  kinematic solver decides which body to pin; roles are arbitrary) via a list of independent
  single-axis movements, each `{motion: rotate|translate, axis, reference, range}`. `unit` is
  dropped (derived from `motion`). Both PLAN and BLOCK declare joints in this vocabulary; a joint
  binds when the block's provided range covers the plan's required range.
- **Blocks may emit more than one union.** A block can produce N rigid bodies (e.g. a hinge's two
  leaves), so a joint can be owned by a single block. The union stays the atom of "rigid printed
  body" (the unit the sweep, plate-clearance, and per-object export operate on); only the
  one-block-one-body assumption is relaxed.
- **Annotation (pseudo) geometry.** Geometry is classified as *printed* (exported + swept) or
  *pseudo* (invisible to export and the sweep, but live for intent checks). Two pseudo kinds:
  a **mating area** (a 2D footprint marking where the block connects) and an **assembly envelope**
  (a 3D volume that must stay clear to assemble the block). The gate checks them.
- **Target pipeline ordering.** The kinematic solver validates the arranged world *in place*,
  and `model_export` serializes the deliverable *after* validation. (Today export runs first to
  produce the STLs the check reads; the target ordering removes that chicken-and-egg by solving
  on live geometry.)

## Capabilities (anticipated, not yet specced)

Likely touches: `joint-classification` / a new `joint-contract` capability (the relational dof +
satisfaction check), `block-library` (multi-union blocks, mating-area + assembly-envelope
descriptors, printed-vs-pseudo geometry), `model-export` (split a result's named sub-bodies into
unions; export after validation), and the kinematic/plate gate stages (contract satisfaction,
mate-area and keep-clear checks). Spec deltas are intentionally deferred until the cruxes resolve.

## Open Questions (blocking implementation)

1. **Satisfaction algebra (crux 1, parked).** Precisely how a requested joint matches a block
   instance: axis-alignment semantics, range subset, and how the plan's `A`/`B` bind to the
   block's two unions. Needs its own exploration.
2. **Sub-body naming convention (crux 2, keystone).** How a multi-union block labels its
   sub-bodies so `model_export` splits them into distinct unions instead of fusing them (today it
   `makeCompound`s one part's solids into one named object). Candidates: a block returns
   `{union_name: Workplane}`; the plan declares which unions a part contains; solids carry tags
   the exporter splits on. The 3MF *output* side (named objects) already exists; this is the
   *input* convention. Everything multi-union rides on this one decision.

## Related in-flight work

- `add-union-interface-type` -- the `union` interface (block fused into the parent body);
  complements the mate-area / assembly-envelope annotations.
- `generalize-joint-axis-interface` -- `joint_axis` is the *geometry-location* half of a joint
  (where the axis is); this change is the *semantics + topology* half (what moves, relative to
  what, how constrained).
