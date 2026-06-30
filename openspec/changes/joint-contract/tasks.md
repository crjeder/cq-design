## Status: BLOCKED — exploratory capture

This change is a captured design direction, not a buildable plan. Implementation tasks are
intentionally not written yet: two design cruxes must resolve first (see `design.md` / `proposal.md`).
Do **not** `/opsx:apply` this change in its current state.

## Decisions to resolve before tasks can be written

- [x] D1. **Satisfaction algebra (crux 1) -- largely RESOLVED for single-axis joints.** A/B binding
      resolved by Topology 1 (the block owns both sides; dof `between` names them). Axis match:
      push block-frame dof vectors through `placement`, then revolute = coaxial, prismatic = parallel.
      Range subset: both sides measured from the authored pose, `wish ⊆ reality`. Exact
      tolerance/inclusivity rules still to spec. **Remaining open fork: spherical/ball** (see D5).
- [x] D2. **Sub-body naming convention (crux 2) -- SHIPPED (Option 3).** Landed on `main` via the
      `multi-union-parts` change: `src/units.py` (`iter_unions`/`resolve_unions`). `union` is a
      first-class plan entity; the plan declares union ids, the script returns a `name -> Workplane`
      map, `model_export` splits per key (N=1 = today's part-id default). See design.md status note.
- [x] D3. **Topology -- DECIDED: Topology 1.** One block owns both sides of a joint and emits them as
      a multi-union dict, carrying the dof that relates them. Inventory rewrite: merge the
      groove/tongue, socket/stud, leaf/leaf half-blocks into joint-owning blocks. See design.md
      "Topology decision (D3)".
- [x] D4. **dof datum + vectors -- DECIDED.** dof carries block-coord vectors; prismatic
      `{direction, limit}`, revolute `{origin (pivot), direction, limit}`; `unit` derived; limits read
      from the authored pose; NO angular reference vector. See design.md "dof vector model (D4)".
- [x] D5. **Spherical/ball satisfaction -- PARKED (option a).** The ball carries no contract dof for
      now; its mate stays a geometry-only check and spherical joins the coupled-multi-DOF TODO. The
      satisfaction algebra ships covering revolute + prismatic only. `ball_socket`/`ball_stud` still
      fuse into one Topology-1 block, but that block declares no `dof` yet.

## Re-scope (2026-06-30): split into shippable slices

With crux 2 (multi-union) already shipped and the cruxes resolved, this stops being one mega-change.
Proposed split:

- [ ] **Slice A -- single-axis joint contract (the shippable core).** Replace the `unit==`-only check
      in `plan_validate._check_kinematics` with the satisfaction algebra: dof vector model
      (D4), Topology-1 inventory rewrite (merge the half-blocks; ball block carries no dof per D5),
      axis-match (placement-transformed: revolute coaxial, prismatic parallel) + range-subset
      (authored-pose datum). Covers revolute + prismatic. This alone closes the
      revolute-vs-ball_socket validation hole.
- [ ] **Slice B -- annotation geometry (separate change).** printed/pseudo classification +
      mating-area (backed-by-own-union-material, foreign keep-out) + assembly-envelope keep-clear.
      Independent of the contract check; spin into its own proposal.
- [ ] **Parked -- spherical/ball contract (D5)** and **coupled/multi-DOF joints** (gimbal, helical
      screw pitch): the multi-DOF TODO. Re-open when a real model needs them.
- [x] ~~Sub-body split / export-after-validate~~ -- the multi-union half SHIPPED (`multi-union-parts`).

DONE this session (no longer dependencies): crux 2 (multi-union), and stacks on
`generalize-joint-axis-interface` (joint_axis) + `add-union-interface-type` (union) -- all merged.
