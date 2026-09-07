## Context

`BUILD_PLAN.json` has two ways to express that two parts meet at one physical
feature, and they carry different guarantees:

- a `joints` entry: the pair's parameters live once in `joints[].params`, and the
  second part's pose is *derived* by `mate_chain.compute_mate_poses`. One source.
- two `interfaces[]` entries, one per part: two independently authored numbers that
  happen to agree today. No source at all -- agreement is a convention held only by
  whoever last edited both files.

Nothing distinguishes them at validation time, so the second form is the cheap
default, and it is the form that ping-ponged.

## Goals / Non-Goals

Goals:
- Make the second form visible at plan time, before any part script exists.
- Cost nothing when a plan is correct, and never fail a plan that was valid before.

Non-Goals:
- Verifying that the two copies agree numerically. `position_mm` is per-part
  authored-frame, so equal numbers mean agreement only when the parts share an
  authoring frame (C5 did; that is not general). Comparing them would need the
  assembled-frame transform, which is exactly what a missing `joints` entry denies.
  The finding is about the *missing derivation*, not about a numeric mismatch.
- The folded-pose coincidence assertion ("the bores line up when the leg lies flat").
  See `TODO.md`; it needs a `kinematics` entry to hang off, and is deferred.

## Decisions

**Key on `interfaces[].name`, not on `position_mm`.** The name is already defined as
"the agreed vocabulary word for this feature" and is already normalized snake_case
(`_check_interface_names`). Two parts using one word for one feature is the semantic
statement we want; equal coordinates are a frame-dependent accident. Keying on
position would miss every model whose parts are authored in their own frames -- the
normal case -- and fire on two parts that merely happen to have a hole at the same
local coordinate.

**Advisory finding, not a validation error.** `check_block_thinness` and
`check_deferred_axis_arms` already established this tier: computed in
`plan_validate.py`, printed by `main()` after the plan passes, excluded from
`validate_plan`'s error list and therefore from the gate's `plan_invalid` path. A
shared vocabulary word for two genuinely independent features is legitimate, and
promoting this to an error would break existing plans. Trade-off accepted: an
advisory can be ignored. It is still strictly more than rule 7's prose, and it is
the only signal that fires *before* the duplicated literal reaches a part script.

**"Linked" means a `joints` entry whose two `members[].part` are the two parts.**
Not "either part appears in some joint" -- C5's failure mode is precisely two parts
that each participate in the model while nothing derives one from the other. With
three or more parts sharing a name, report the name once, listing the parts that no
single joint links pairwise.

## Risks

- Noise on models that reuse a vocabulary word deliberately. Mitigated by the
  advisory tier and by naming the parts in the message, so it is a one-glance
  dismissal.
- The finding fires at plan time, when the planner may legitimately not know yet
  whether the mate is a matched-pair block. It points at `joints`; it does not
  demand a specific block.
