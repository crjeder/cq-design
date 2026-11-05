## ADDED Requirements

### Requirement: Step runs are recorded in script history
`step_worker.py run` SHALL record each run through `script_history.record_run` with `ok`
true only when every step passed and the full tier, when it ran, succeeded; with the plan
revision it computes for `steps.jsonl`; and with the `--suppress` ids when any were given.
It SHALL set `CQ_HISTORY_SKIP=1` on the full-tier `run_cadquery_model.py` subprocess so
the run is recorded once. Warm and fallback runs SHALL record the same way.

#### Scenario: Failing step is recorded
- **WHEN** a step run fails at step 3
- **THEN** `build/history/<part>/log.jsonl` gains one `run` event with `ok: false` and the
  script's `src`

#### Scenario: Fallback run is recorded
- **WHEN** the worker crashes and the run is served cold (`worker: "fallback"`)
- **THEN** exactly one `run` event is recorded for it
