## Why

A part's `placement` is authored by the planner in Phase 2, but the geometry it
transforms is authored by a different agent in Phase 3. `placement` is only correct if
the part author happens to build in the frame the planner assumed -- and that assumption
is never stated in any field the author receives. Today the planner compensates by
narrating the frame convention into `planning_notes` ("panel WIDTH along authored +X,
THICKNESS along authored Z"), a field with no reader: `prompts/part.md`,
`skill/phase3_build.md`, `skill/phase4_deliver.md`, and every `src/*.py` reference it
zero times. The coupling holds by luck, or by the planner duplicating the convention
into `part_notes`.

The plan already contains the correct pattern in its other pose mechanism: a `joints`
mate chain DERIVES a part's assembled pose from the geometry the author actually built
(block dock frames composed by `mate_chain.compute_mate_poses`). This change makes the
`placement` path work the same way -- pose becomes an output of authoring, not an
unstated precondition of it.

## What Changes

- **BREAKING (plan-authoring contract):** the Phase 2 planner no longer writes
  `parts[].placement`. The Phase 3 part author writes it, as a write-back into
  `BUILD_PLAN.json` after its part is accepted -- the same write-back principle already
  used for `dimensions` (`skill/phase3_build.md:552`) and `load` (`:621`). Existing
  plans that carry a planner-written `placement` stay valid and are treated as the
  author's starting proposal.
- New optional per-part field `pose_intent` (string): the planner states the assembled
  pose as a goal in human-readable terms ("stands upright, outward face toward world
  -Y, at the tower's NE corner") instead of as a transform. This is the compact,
  human-relevant pose field; `placement` remains the machine truth the human can skip.
- `prompts/part.md` gains a `{{POSE_INTENT}}` placeholder and a contract rule: the
  author picks its own authoring frame freely and reports the transform that carries
  that frame into the stated assembled pose.
- The plan is re-validated (`plan_validate.py`) after the last part's write-back and
  before model export, because the joint-contract axis arm compares a block's `dof`
  axis *after* `placement` and can no longer do so at Phase 2 time.
- **No new pose representation.** A transformation matrix was considered and rejected:
  the existing `{rotate: [{axis, angle_deg}], translate_mm}` is shorter and more legible
  to both audiences than 16 floats, and a stored matrix would not round-trip (which is
  precisely why `placement.apply_matrix` exists alongside `apply_cq` for `mate_chain`'s
  derived poses). The schema's `placement` shape is untouched.
- **No new Python module.** The handback rides the existing plan write-back path; only
  the schema gains one optional string.

## Capabilities

### New Capabilities
- `assembled-pose-handback`: the planner-to-author pose contract -- the planner declares
  the assembled pose as intent, the author chooses its authoring frame and returns the
  `placement` that satisfies that intent, and the plan is re-validated before export.

### Modified Capabilities
- `planning-phase`: the planner declares `pose_intent` rather than authoring
  `parts[].placement`; the part-object field list gains `pose_intent`.
- `part-authoring-guidance`: the part author gains an obligation to report the
  assembled-frame transform for the frame it chose.
- `joint-contract`: the axis arm is checked against a `placement` that is absent during
  Phase 2 validation, so the contract is enforced at the pre-export re-validation.

## Impact

- `src/build_plan_schema.json` -- one new optional `parts[].pose_intent` string.
- `prompts/planning.md` -- rule 8 rewritten (declare intent, not transform); rule 7's
  `root_part` "anchored by its own placement" wording; the schema example.
- `prompts/part.md` -- new `{{POSE_INTENT}}` placeholder and contract rule.
- `skill/phase3_build.md` -- substitution table row, the write-back step, and the
  pre-export re-validation call.
- `skill/phase2_planning.md` -- the plan summary surfaces `pose_intent` per part.
- `src/plan_validate.py` -- the kinematics axis arm reports that it deferred rather than
  silently treating an absent `placement` as identity.
- Unaffected: `placement.py`, `mate_chain.py`, `model_export.py`, `kinematic_check.py`,
  `plate_clearance_check.py`, `keep_out_check.py`, `build_template.py` -- all consume
  `placement` at export time or later, after the write-back has happened.
- `evals/cases/*/BUILD_PLAN.json` goldens keep their existing `placement` values (valid
  as author proposals); no golden regeneration.
