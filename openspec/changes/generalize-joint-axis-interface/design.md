# Design: generalize-joint-axis-interface

## Decision 1: Rename, don't alias

`hinge_axis` is replaced by `joint_axis` and removed from the vocabulary, rather than kept as
a deprecated alias. Interface `type` values appear only in `blocks/inventory.json` (which the
project owns) and are validated against the closed set; no `BUILD_PLAN.json`, runtime code, or
external consumer authors them. So the rename is total and safe: migrate the three users, drop
the old token. Keeping both would re-create the grab-bag the TODO is trying to remove.

## Decision 2: `joint_axis` semantics -- one token, motion from `dof`

`joint_axis` marks the block's kinematic reference for whatever joint it forms; the motion
*kind* is not encoded in the interface token but read from the block's `dof.type`:

- revolute -> the rotation axis line
- prismatic -> the translation axis line
- spherical -> the pivot center

A flexure (`living_hinge`) has no rigid `dof`; its `joint_axis` marks the bend axis, with no
`dof` present. This mirrors how the kinematic check already derives motion from `dof`/the plan
`kinematics`, never from the interface token -- so generalizing the token changes vocabulary and
documentation, not behavior.

## Decision 3: Keep geometry docks and the feature axis separate

`ball`/`ball_socket` and `sliding_interface` are **mating-geometry** tokens: they describe the
dock that physically captures a mate (a socket cupping a ball, a groove capturing a tongue),
independent of the abstract DOF reference. `axis` is a **feature** axis (e.g. a `teardrop_bore`
cylinder centerline), not a joint. None of these is the joint-DOF reference, so none is renamed.
A block may legitimately carry both a geometry dock and a `joint_axis` (e.g. a future slider
could declare `sliding_interface` for its rail plus `joint_axis` for its travel line); the
existing hinge blocks need only `joint_axis` because the knuckle *is* the axis.

## Decision 4: Migration set is exactly the current `hinge_axis` users

Only `hinge_leaf`, `pin_hinge`, and `living_hinge` declare `hinge_axis` today. Each becomes
`joint_axis` with the same `orientation`/`origin`. `hinge_leaf` and `pin_hinge` keep their
revolute `dof`; `living_hinge` stays dof-less. The dovetail (prismatic) and ball (spherical)
blocks already use geometry tokens and are intentionally left alone (Decision 3).

## Decision 5: Spec edits are token swaps, not new requirements (mostly)

Four capabilities mandate or list `hinge_axis`:

- `block-library` -- the closed-set vocabulary list, and the `union` requirement's parenthetical
  examples (both introduced/realigned by the `add-union-interface-type` change). Swap the token,
  and add one requirement defining `joint_axis` semantics.
- `joint-classification` -- "Inventory schema permits the taxonomy fields" lists `hinge_axis` in
  the mandated enum subset. Swap the token.
- `living-hinge` / `pin-hinge` -- each requires the block to declare a `hinge_axis` interface.
  Swap the token (orientation `+Y` and the rest unchanged).

Because the `block-library` deltas edit requirements that `add-union-interface-type` (PR #13)
created, this change stacks on #13; applied after it, every swap is a clean find-replace.

## Test approach

- `joint_axis` on a minimal descriptor validates; `hinge_axis` (now retired) is rejected like any
  unknown type.
- The shipped `inventory.json` validates and contains no remaining `hinge_axis` interface.
- Existing hinge/flex block geometry tests are unaffected (the rename is metadata-only).
