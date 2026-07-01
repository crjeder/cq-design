## Status: BLOCKED — exploratory capture

This change is a captured design direction, not a buildable plan. Implementation tasks are
intentionally not written yet: two design cruxes must resolve first (see `design.md` / `proposal.md`).
Do **not** `/opsx:apply` this change in its current state.

## Decisions to resolve before tasks can be written

- [x] D1. **Satisfaction algebra (crux 1) -- single-axis SHIPPED** via `single-axis-joint-contract`
      (archived). type + placement-transformed axis (revolute coaxial, prismatic parallel) + range vs
      `mechanical_limit`; spherical skipped. NOTE: the earlier "A/B binding resolved by Topology 1"
      claim was corrected -- binding is only trivial when both members share a part; across parts it
      is the D6 work. **Remaining open fork: spherical/ball** (see D5).
- [x] D2. **Sub-body naming convention (crux 2) -- SHIPPED (Option 3).** Landed on `main` via the
      `multi-union-parts` change: `src/units.py` (`iter_unions`/`resolve_unions`). `union` is a
      first-class plan entity; the plan declares union ids, the script returns a `name -> Workplane`
      map, `model_export` splits per key (N=1 = today's part-id default). See design.md status note.
- [x] D3. **Topology -- DECIDED: matched-pair block (Topology 1, corrected rationale).** One block is
      the single source of a matched pair (A mates B iff same params), emitting both members as a
      multi-union dict + the dof relating them. Applies to ALL mating pairs (hinge, dovetail, ball) --
      manufacturing (print-in-place vs separate) is irrelevant. The lone-half `hinge_leaf` is retired.
      See design.md "Topology decision (D3)".
- [x] D4. **dof datum + vectors -- DECIDED (shipped in single-axis-joint-contract).** dof carries
      block-coord vectors; prismatic `{direction, mechanical_limit}`, revolute
      `{origin (pivot), direction, mechanical_limit}`; unit derived; limits from the authored pose; NO
      angular reference vector. See design.md "dof vector model (D4)".
- [x] D5. **Spherical/ball satisfaction -- PARKED (option a).** The ball carries no contract dof for
      now; its mate stays a geometry-only check and spherical joins the coupled-multi-DOF TODO.
- [x] D6. **Composition + pair binding -- DECIDED: Option B.** A joint's two members are `union`s
      fused into parent parts (possibly DIFFERENT parts); a plan-level `joint` entity binds the pair to
      its single parametric source so a mismatched pair is machine-caught. This is where the A/B
      binding actually lives. Open sub-questions (joint entity shape, cross-script member fan-out,
      contract read path) are the core of the next change. See design.md "DECISION (D6)".

## Re-scope (2026-06-30): split into shippable slices

With crux 2 (multi-union) already shipped and the cruxes resolved, this stops being one mega-change.
Slices:

- [x] **Slice A -- single-axis joint contract -- SHIPPED & ARCHIVED** (`single-axis-joint-contract`).
      dof vector model (D4) + type/axis/range satisfaction in `plan_validate._check_kinematics`,
      revolute + prismatic. Closed the `unit==`-only hole. NOTE: this slice was scoped
      contract-check-ONLY -- it did NOT merge the half-blocks (that is Slice B below).
- [ ] **Slice B -- matched-pair joint blocks + plan-level `joint`/mate model (D3 + D6) -- NEXT.**
      Merge hinge/dovetail/ball half-blocks into matched-pair blocks that emit both member-`union`s
      (each with ONE mate pad); retire the lone-half `hinge_leaf`; add the plan-level `joint` entity +
      the mate model. Most D6 sub-questions are now resolved (see design.md "D6 refinements"):
      params via `parameters.py`; fusion in the assembled frame; pads dock member->part (not
      pad<->pad); coaxiality is a block input that + pad docks DERIVE part poses along a mate chain
      from a root; where/orientation is a PLAN duty (D6b), geometry only realizes the seating; the
      `kinematics` entry is derived from the `joint`. Assembly structure is a recursive kinematic
      TREE (D7): `placement`+`joint` unify into one parent edge (fixed or DOF); a movable edge re-poses
      the subtree (series chains for free); flat plans = depth-1 trees (free migration); tree-only
      (closed loops parked); a node does NOT know its parent (edge is parent-owned). **Still open
      before buildable:** the plan-TREE shape -- nested children vs a flat edge/`joints[]` list keyed
      by parent; how the root is marked (edge parent = `world`); the matched-pair joint edge (block +
      params + DOF + which member fuses into parent vs child); and root-anchor validation
      (unreachable/double-anchored nodes).
- [ ] **Slice C -- annotation geometry (separate change).** printed/pseudo classification +
      mating-area (backed-by-own-union-material, foreign keep-out) + assembly-envelope keep-clear.
      Independent of the joint blocks; spin into its own proposal.
- [ ] **Parked -- spherical/ball contract (D5)** and **coupled/multi-DOF joints** (gimbal, helical
      screw pitch): the multi-DOF TODO. Re-open when a real model needs them.
- [x] ~~Sub-body split / export-after-validate~~ -- the multi-union half SHIPPED (`multi-union-parts`).

DONE this session (no longer dependencies): crux 2 (multi-union), and stacks on
`generalize-joint-axis-interface` (joint_axis) + `add-union-interface-type` (union) -- all merged.
