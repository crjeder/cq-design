## Why

The planner writes both the design and the checks that verify it (`interfaces[]`,
`probes[]`), so a requirement it misreads or drops loses its check too. Nothing fails, and
the builder fills the gap by guessing (cgb-v1 run 125: hole positions given in the request
never reached the plan). The only bar that measures against the request is an advisory LLM
reading a render. An independent agent that turns the approved intent into testable
statements, plus a script that requires the plan to bind and satisfy every one, makes a
dropped or misread requirement a hard failure.

## What Changes

- New **oracle** agent role (`agents/oracle.md`, `prompts/oracle.md`, `models.oracle`). It
  reads the user's request, the draft Phase 1 reformulation, and the dimension table, never
  the plan, and writes `acceptance.json`: numbered statements `S1..Sn`, each citing a
  verbatim span of the intent.
- Statements come from a closed, frame-free vocabulary (`part_count`, `feature`, `fit`,
  `spacing`, `extent`, `probe`) that a script can check. Anything a script can't check is
  tagged `visual` and becomes a Visual Review Checklist question.
- **Phase 1 exit checkpoint** gets a fourth item: the oracle's statements, shown in plain
  words. The user approves or corrects them together with the reformulation. A correction
  goes into the intent, never straight into a statement, and the oracle is re-run.
- **Option C binding**: the planner must bind every non-`visual` statement to plan entities
  (`acceptance_bindings` in `BUILD_PLAN.json`). `plan.py validate` reports an unbound
  statement, or a bound entity that contradicts its statement, as a blocking error. The
  planner fixes these in its existing self-retry loop (3 attempts) and then returns
  `blocked` to the user.
- New `src/oracle.py` (`validate`, `check`, `verify`) and a quality-gate `oracle` stage.
  `verify` checks bound statements against the built geometry and emits `source: "oracle"`
  issues naming the statement. These go to the builder for correction. After 3 rounds on
  the same statement the part is blocked and escalated to the user.
- **Staleness**: new `BUILD_PLAN.json` field `acceptance_ts`. `plan.py validate` fails when a
  `clarification`/`correction` entry in `request_log` is newer than `acceptance_ts`, the
  same rule as `intent_ts`. `log.py request add` gets `--acceptance-reconciled`.
- `plan.py summary` shows each statement with its binding at the plan checkpoint.
- Plans without `acceptance.json` (eval goldens, legacy plans) skip every oracle check.

## Capabilities

### New Capabilities
- `oracle-acceptance`: the oracle role, the `acceptance.json` contract and statement
  vocabulary, the intent-citation rule, `visual` tagging, Phase 1 presentation, binding
  validation, geometric verification, the 3-round correction cap, and `acceptance_ts`
  staleness.

### Modified Capabilities
- `agent-definitions`: adds `agents/oracle.md` to the required set, with its tool list.
- `model-routing-config`: adds the `oracle` role key.
- `approved-intent`: the Phase 1 exit checkpoint also covers the oracle statements; a
  statement correction is applied to `intent`.
- `request-relative-acceptance`: `visual` oracle statements become blocking checklist
  questions; the free-form request-conformance finding stays advisory.

## Impact

- New: `agents/oracle.md`, `prompts/oracle.md`, `src/oracle.py`, `acceptance.json` (project
  root, written by the oracle), `tests/test_oracle.py`.
- Changed: `src/build_plan_schema.json` (`acceptance_bindings`, `acceptance_ts`),
  `src/plan.py` (validate + summary), `src/render_prompt.py` (`oracle` kind),
  `src/quality_gate.py` (oracle stage), `src/log.py` (`--acceptance-reconciled`),
  `src/skill_config.default.json`, `prompts/planning.md`, `prompts/audit.md`,
  `skill/phase1_requirements.md`, `skill/phase2_planning.md`, `skill/phase3_build.md`,
  `skill/resume.md`, `reference/scripts.md`, `FILES.md`, `ARCHITECTURE.md`,
  `init_permissions.py` / `skill_permissions.json` if the oracle needs new allow entries.
- Cost: one extra agent call per design, plus one re-run per intent correction. It runs
  during Phase 1, before the planner exists, so the planner is not delayed.
