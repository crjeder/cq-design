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
- [ ] **Slice B -- matched-pair joint blocks + plan-level `joint` binding (D3 + D6) -- NEXT.** Merge
      hinge/dovetail/ball half-blocks into matched-pair blocks that emit both member-`union`s; retire
      the lone-half `hinge_leaf`; add the plan-level `joint` entity that binds the pair to one
      parametric source and fans each member into its parent part (possibly a different part). Resolve
      the D6 open sub-questions first (joint entity shape; cross-script member fan-out via the `union`
      interface; how the shipped contract reads the `joint` binding). This is the real remaining
      Topology-1 work.
- [ ] **Slice C -- annotation geometry (separate change).** printed/pseudo classification +
      mating-area (backed-by-own-union-material, foreign keep-out) + assembly-envelope keep-clear.
      Independent of the joint blocks; spin into its own proposal.
- [ ] **Parked -- spherical/ball contract (D5)** and **coupled/multi-DOF joints** (gimbal, helical
      screw pitch): the multi-DOF TODO. Re-open when a real model needs them.
- [x] ~~Sub-body split / export-after-validate~~ -- the multi-union half SHIPPED (`multi-union-parts`).

DONE this session (no longer dependencies): crux 2 (multi-union), and stacks on
`generalize-joint-axis-interface` (joint_axis) + `add-union-interface-type` (union) -- all merged.
