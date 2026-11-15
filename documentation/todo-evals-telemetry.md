# Evals, telemetry and failure mining -- details

Tasks: [TODO.md](../TODO.md#2-evals-telemetry-and-failure-mining). Items come from the related-project survey ([related_projects.md](related_projects.md)); each is one openspec change with one runnable test. Item 1 produces the evidence item 2 needs.

### Test cases to add

Salacia case
- [ ] [SUP Silencer](https://makerworld.com/de/models/2871437-paddleboard-sup-deflation-silencer#profileId-3205902)
- [ ] beamer-halter

### Per-attempt efficiency telemetry

Source: SmartAI/Chamfer, rated Medium-High.

- Why: `build/attempts.jsonl` (`src/log.py`, `validate_attempt`) holds only
  `part_id, attempt, outcome, error_types, prompt_chars, model, visual_review, ts`.
  `src/session_cost.py` already gives billed cost per *session* (`build/cost.json`);
  nothing says where wall-clock or tool time goes per attempt or per tool.
- Do: (a) `log.record_attempt` accepts and stores optional `wall_ms` (time around the
  `run_cadquery_model.py` subprocess; the wrapper's `--attempts-log` path is the
  reliable source because the PostToolUse hook does not see sub-agent calls, see the
  `hooks skip sub-agent tool calls` memory) and `cadquery_import_ms` (cold OCC import,
  measured in `run_model_shim.py`). (b) `render_preview.py` and the check CLIs append
  `{tool, part_id, ms, payload_bytes}` to `build/tool_calls.jsonl`. (c) Keep every new
  field OPTIONAL in `validate_attempt`; old logs must stay valid. (d)
  `evals/run_evals.py` `attempt_metrics` adds `mean_wall_s_per_attempt`, per-tool
  totals and render count, shown in `render_markdown`; `n/a` when absent.
- Test: `tests/test_log.py` (old record validates, new optional fields validate, bad
  type rejected) and `tests/test_run_evals.py` (metrics with and without the fields).
- Done when: a scorecard row shows wall time and render count, and a log written
  before this change still scores.

### Failure-mode mining

Source: SmartAI/Chamfer, rated Medium-High.

- Why: Chamfer killed 11 of 15 failed tool calls with four sentences of environment
  facts, each traced to a counted failure. Our equivalent facts are scattered over
  `prompts/part.md` and `skill/phase3_build.md`. Needs item 1's data or the existing
  `error_types` field.
- Do: (a) new `python src/log.py attempt stats <attempts.jsonl> [--top N]` printing
  `error_types` frequency over `fold_attempts` records, and the types that occur on
  a failed attempt immediately followed by a pass. Also usable on eval run dirs
  (`evals/run_evals.py` `read_attempts`). (b) For each type with >= 3 occurrences in
  >= 2 parts: if `script_lint.py` can catch it deterministically, add a lint rule
  instead; otherwise add ONE line to a new "Run environment facts" block placed
  before "### Contract rules" in `prompts/part.md`, with the count and date in a
  comment. (c) Assert in `tests/test_render_prompt.py` that the block renders.
- Done when: `attempt stats` runs on a real `attempts.jsonl`, and each fact line
  traces to a counted class.

### Under-specified eval cases

Source: ProCAD, CadAgent; intent-recognition item 5.

- Why: every case in `evals/cases/` is well specified, so no elicitation or
  assumption change can regress and the scorecard cannot see it. It is the gate on
  items 5 and 6 and on `spec audit` work.
- Do: (a) 4 new cases under `evals/cases/` whose `request.md` omits one named
  category each (missing dimension, conflicting constraint, unstated frame, unstated
  fit/load), plus 2 well-specified controls; `case.json` gets
  `expect: {"ask": true|false, "category": "..."}`. (b) `run_evals.py` scores
  `asked_when_needed` and `asked_when_not` from the run's `request_log`
  `clarification` entries (and `assumption` entries once item 5 lands), reported
  separately so asking about everything cannot win. (c) `tests/test_eval_corpus.py`
  validates the new `expect` block; `tests/test_run_evals.py` scores a fixture run.
- Done when: the scorecard prints both rates and a control case that triggers a
  question lowers `asked_when_not`.
