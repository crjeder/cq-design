## Why

The C5 Phone-Holder model joins two parts with a real revolute filament-pin hinge,
but `cradle.py` and `plate.py` each hardcode their own `PIVOT_Y`/`PIVOT_Z` literal
for the *same physical axle*. Round 9 of that session hand-edited `plate.py`'s
`PIVOT_Z` from 6.0 to 13.5 "to match" a cradle-only correction, silently undoing
round 8's user-requested plate-ear position (see `TODO.md`, "C5 knuckle pivot
ping-pong"). The strings `joints`, `root_part`, `kinematics` and `pin_hinge` appear
zero times in that session's transcript.

The sanctioned mechanism already exists and was simply never reached:
`prompts/planning.md` rule 7 requires a cross-part matched pair to become a `joints`
entry, `blocks.joints.pin_hinge` carries `emits: [leaf_a, leaf_b]`, and
`mate_chain.py` would have *derived* the plate's pose so the second literal would
not exist. Rule 7 is prose only. `plan_validate.py` validates the `joints` entries a
plan has, but cannot notice that one is missing -- and it explicitly permits the
same interface `name` on two different parts ("the part id disambiguates them"),
which is exactly the fingerprint of one shared physical feature typed twice.
`feature_presence_check.py` then checks each copy against its own part's authored
frame, so both pass.

## What Changes

- Add `plan_validate.check_shared_interfaces(plan)`: a plan-only advisory finding
  (no CadQuery, no mesh) reporting each `interfaces[].name` that appears on two or
  more parts which no `joints` entry links, naming the parts and pointing at
  `joints` / `mate_chain.py` as the derivation route.
- Print those findings from `plan_validate.main()` after `BUILD_PLAN OK`, alongside
  the existing `check_block_thinness` and `check_deferred_axis_arms` findings.

Advisory, not an error: two parts legitimately share a vocabulary word for
independent features (two unrelated `vent_slot`s), and an existing plan with a
shared name must keep validating. The finding is the nudge that rule 7 currently
lacks; the hard rule stays orchestrator discipline
(`openspec/specs/request-log/`, parameter-scope routing).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `joint-mate-entity`: add the plan-time advisory for an unlinked shared interface
  name.

## Impact

- `src/plan_validate.py`: one new function plus three lines in `main()`. Reuses the
  existing findings-list convention; `validate_plan`'s error contract is unchanged.
- `tests/test_plan_validate.py`: cases for flagged / linked / single-part /
  unnamed. Fast, no CadQuery.
- `prompts/planning.md` rule 7: one sentence naming the finding, so the planner
  knows what triggers it.
- No schema change (`interfaces[].name` and `joints` both already exist), no CLI
  flag, no exit-code change.
