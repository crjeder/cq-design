## 1. Schema: review_policy field

- [x] 1.1 Add `review_policy` enum (`minimal` | `checkpoints` | `every_stage`) to
      `src/build_plan_schema.json` as an optional plan-level field.
- [x] 1.2 Confirm `src/plan_validate.py` needs no code change (draft-7 enum
      validation is schema-only); add a regression test in
      `tests/test_plan_validate.py` covering a valid value, an invalid value, and
      an omitted field defaulting to `every_stage` semantics downstream.

## 2. Planning prompt and summary

- [x] 2.1 Update `prompts/planning.md` to elicit the user's review-frequency
      preference and record it as `review_policy`, following the existing
      `optimize_for` elicitation pattern.
- [x] 2.2 Update the plan-summary generation step (wherever `skill/phase1_requirements.md`
      or `skill/phase2_planning.md` documents the summary) to surface the
      effective `review_policy` (declared or defaulted) in the printed summary.

## 3. Profile stub review (Step 0)

- [x] 3.1 Document Step 0 (stub authoring + render) in `skill/phase3_build.md`,
      ahead of the existing Step 1 ("Match archetype").
- [x] 3.2 Define the stub script shape (profile-only extrusion, nominal
      thickness) and its `run_cadquery_model.py --preview` invocation in the
      Step 0 documentation.
- [x] 3.3 Document the checkpoint behavior split: `checkpoints`/`every_stage`
      pause for user approval/change/skip; `minimal` self-reviews without
      pausing.
- [x] 3.4 Add the `stub_mismatch`-style self-review flow wording (or reuse
      `visual_mismatch` framing) for the `minimal` self-review path, so it's
      clear this is not a silent skip.

## 4. Progressive-build gate rework

- [x] 4.1 Update `skill/phase3_build.md`'s progressive-build gate section to
      read `review_policy` first: `every_stage` -> always progressive,
      `checkpoints` -> today's complexity gate, `minimal` -> always autonomous.
- [x] 4.2 Keep the complexity-gate threshold values documented (still used under
      `checkpoints`) but no longer presented as the default behavior.
- [x] 4.3 Update the user-override wording (force progressive / force
      autonomous) to reference overriding the `review_policy`-driven selection
      rather than "the gate."

## 5. Tests and docs

- [x] 5.1 Add/update tests exercising `review_policy` validation in
      `tests/test_plan_validate.py` (task 1.2 covers the cases; this task is
      the checkpoint that they're wired into the suite and passing).
- [x] 5.2 Update `IMPROVEMENT_PLAN.md` row for item 4 to `DONE` once merged,
      matching the convention used for items 1-3, 6-8, 11-13.
- [ ] 5.3 Run the eval harness (`evals/run_evals.py`, score-only mode) before
      and after, per the design doc's latency-risk mitigation, to confirm the
      added stub step doesn't regress cost-per-accepted-part materially.
      Deferred: this change is documentation/schema-only (no code path runs
      the new Step 0 or gate logic yet -- both are prose Claude follows at
      run time), so there is no code change for the harness to score against.
      Run it once real build sessions have exercised `review_policy` in the
      field.

## 6. Validation

- [x] 6.1 Run `uv run pytest tests/test_plan_validate.py` (fast subset).
- [x] 6.2 Run the full suite (`uv run pytest tests/`) before merging. 573 passed.
- [ ] 6.3 Manually walk one plan through Phase 3 with each of the three
      `review_policy` values to confirm the Step 0 stub and progressive-build
      gate behave as specced. Deferred: requires an interactive Phase 3 run
      with a live user, not something this session can execute standalone.
