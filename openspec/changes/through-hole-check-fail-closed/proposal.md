## Why

The b1 gate check from `through-hole-genus-check` (#395) caught a wrong hole count in only
one of the six fixtures in the 2026-11-22 CADGenBench runs (`cgb-104-119-150-opus` and
`-sonnet`), and the agent then defeated it in that one. Fixture 104's drawing calls out
4x Ø9.2 THROUGH, 4x Ø4.8 THROUGH and a through bore (b1 9). The plan said 9, the build
had 6, and round 1 of the gate reported `through_hole_count_mismatch`. The agent then set
three interfaces to `through_count: 0` and round 2 passed. This edit was not logged
anywhere. In the other four fixtures besides 104 and opus/119, the check never ran: two had no `BUILD_PLAN.json`, and two had a
plan with `interfaces: []`. The check is opt-in, so it skipped silently, and so did the
through/blind drawing rule in `prompts/planning.md`.

Two causes: the gate trusts a plan the agent can edit after approval, and the check fails
open when the plan declares nothing.

## What Changes

- `pipeline.py advance phase2/plan_approved` appends each part's planned b1 (the sum of its
  interfaces' `through_count`) to the journal line, the same way `part_accepted` appends
  `sha=`. The gate takes the planned b1 from the latest valid `plan_approved` line, not
  from the live plan. To change a count you re-approve the plan, which already voids every
  `part_accepted` built on the old approval (forcing a rebuild).
- When the live plan's total differs from the approved one, the mismatch issue reports both
  (`approved_b1`, `plan_b1`) and says that the plan was edited after approval.
- Under `design_intent: "cad"` the b1 check always runs: a missing `through_count` counts
  as 0, so a part with no declared interfaces but built through holes fails the gate. Print
  intent keeps today's opt-in behaviour.
- `evals/cadgenbench_run.py` prompts generation fixtures with `/cq-design:design` instead of
  "Use the cq-design skill", so the pipeline always loads. After generation it audits each
  generation fixture's work directory and writes a `pipeline` block per fixture to
  `sanity.json`: is there a plan, a valid `gate_result` and passed gate reports, and did the
  b1 check run. The console summary counts fixtures that bypassed the pipeline.

## Capabilities

### New Capabilities
- `cadgenbench-pipeline-audit`: the runner's slash-command prompt for generation fixtures
  and its post-run audit that each fixture went through plan, gate and b1 check.

### Modified Capabilities
- `through-hole-count-check`: the planned b1 comes from the plan-approval record, and the
  check is always on under CAD intent.
- `pipeline-state-machine`: `plan_approved` records each part's planned b1.

## Impact

- `src/pipeline.py`: `advance` appends `b1=<part>:<n>,...` on `phase2/plan_approved`, plus a
  reader for the latest valid value.
- `src/quality_gate.py`: `_through_hole_issues` takes the approved b1 and the CAD flag.
  `run_gate` passes them in.
- `evals/cadgenbench_run.py`: `build_prompt`, a new audit step in `main`, and `sanity.json`
  shape.
- `skill/phase3_build.md`: under Quality gate, a `through_hole_count_mismatch` is fixed in
  the part script, never by editing `through_count`. A count change goes back through plan
  approval.
- `reference/scripts.md`, `evals/README.md`: contract updates.
- Tests: `tests/test_pipeline.py`, `tests/test_quality_gate.py`,
  `tests/test_cadgenbench_run.py`.
