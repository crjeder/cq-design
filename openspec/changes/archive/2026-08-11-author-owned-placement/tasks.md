## 1. Schema

- [x] 1.1 Add optional `pose_intent` (string) to `parts[].properties` in
      `src/build_plan_schema.json`, with a description stating it is the goal pose in the
      assembled frame and never a restatement of the rotation/translation. Required
      because `parts[].items` sets `additionalProperties: false`, so the field is
      rejected until declared.
- [x] 1.2 Update the `parts[].placement` schema description: the field is supplied by the
      part author during the build phase; a value present before then is a proposal.
- [x] 1.3 Add a `test_plan_validate.py` case: a plan with `pose_intent` validates, and a
      plan with neither `pose_intent` nor `placement` still validates.

## 2. Planning prompt and phase

- [x] 2.1 Rewrite `prompts/planning.md` rule 8: declare the assembled pose as
      `pose_intent`; do not author `placement`. Keep the rule number stable (rule numbers
      1-13 are cross-referenced by number from `skill/phase2_planning.md` and
      `skill/phase3_build.md`).
- [x] 2.2 Update `prompts/planning.md` rule 7's `root_part` wording ("anchored by its own
      `placement`") so the anchor is author-supplied, and keep the standing rule that a
      mate-chained part never carries a placement.
- [x] 2.3 Update the schema example near `prompts/planning.md:293` to show `pose_intent`
      instead of a `placement` block.
- [x] 2.4 Add a rule banning prose restatement of a pose transform in `planning_notes` /
      `part_notes` -- the structured `placement` and the one-line `pose_intent` are the
      only two places a pose is expressed.
- [x] 2.5 Update `skill/phase2_planning.md`'s plan-summary section to render each part's
      `pose_intent` and to not render rotation/translation values.

## 3. Part prompt and build phase

- [x] 3.1 Add `{{POSE_INTENT}}` to `prompts/part.md`'s part specification section, next to
      `{{PART_NOTES}}`.
- [x] 3.2 Add the handback to `prompts/part.md`'s enumerated Contract rules: report the
      assembled-frame transform (ordered `rotate` steps then `translate_mm`) that carries
      the authored geometry into the stated pose intent; report nothing when the authored
      geometry is already in that pose, or when the part is mate-chained.
- [x] 3.3 State in `prompts/part.md` that the authoring frame is the author's choice, and
      re-word any frame guidance as a recommendation rather than a precondition.
- [x] 3.4 Add the `{{POSE_INTENT}}` row to `skill/phase3_build.md`'s substitution table,
      giving its cold and inline values (`part["pose_intent"]`, or an explicit `(none)`).
- [x] 3.5 Add the write-back step to the part loop in `skill/phase3_build.md`, after the
      part is accepted: write the author's `placement` into `BUILD_PLAN.json`, following
      the `load` write-back wording at `:621` as the model.

## 4. Validation timing

- [x] 4.1 In `src/plan_validate.py`'s `_check_kinematics` axis arm, when the moving
      union's part has no `placement`, skip the axis/coaxiality comparison and collect a
      deferred-axis-arm advisory instead of comparing an untransformed block axis.
- [x] 4.2 Surface those advisories through `main()` in the same non-fatal shape as
      `check_block_thinness` findings (printed after `BUILD_PLAN OK`, exit 0).
- [x] 4.3 Add `test_plan_validate.py` cases: a kinematics entry whose part has no
      placement produces the advisory and no error; the same entry with a placement that
      rotates the block axis off `axis_dir` still produces the `joint_contract` error.
- [x] 4.4 Add the pre-export `plan_validate.py` run to `skill/phase3_build.md`'s Model
      export section, before the `model_export.py` invocation, stating that a failure
      blocks the export.

## 5. Documentation and corpus

- [x] 5.1 Update `CLAUDE.md`'s `src/plan_validate.py` row to mention the deferred axis arm
      and the pre-export re-validation.
- [x] 5.2 Run `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` and
      confirm the eval-corpus goldens still validate unchanged (their planner-written
      placements stay valid as proposals, per design D6).
- [x] 5.3 Update the two TODO.md items this change came out of ("pose-intent field" and
      the header item above it) to point at this change instead of restating its open
      questions.
