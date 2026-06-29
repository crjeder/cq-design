## Status: BLOCKED — exploratory capture

This change is a captured design direction, not a buildable plan. Implementation tasks are
intentionally not written yet: two design cruxes must resolve first (see `design.md` / `proposal.md`).
Do **not** `/opsx:apply` this change in its current state.

## Decisions to resolve before tasks can be written

- [ ] D1. **Satisfaction algebra (crux 1, OPEN).** Define how a requested joint matches a block
      instance: axis-alignment semantics (parallel? coaxial?), range subset rule, and how the plan's
      `A`/`B` bind to a block's two unions. Resume the explore thread.
- [x] D2. **Sub-body naming convention (crux 2) -- DECIDED: Option 3.** `union` becomes a first-class
      plan entity; the plan declares a build unit's union ids, the script returns a
      `name -> Workplane` map, `model_export` splits per key (N=1 = today's part-id default). Blast
      radius: plan schema (`unions` field, plate moves part->union), the `result` contract, and
      `model_export`. See design.md "DECISION (crux 2 / D2)".

## Sequencing once decided (sketch, not committed)

- [ ] Likely split into smaller changes rather than one mega-change:
      (a) joint-as-contract vocabulary + satisfaction check (depends D1),
      (b) multi-union blocks + result sub-body split + export-after-validate (depends D2),
      (c) annotation geometry: printed/pseudo classification + mating-area + assembly-envelope checks.
- [ ] Stacks on `generalize-joint-axis-interface` (joint_axis geometry half) and
      `add-union-interface-type` (union interface).
