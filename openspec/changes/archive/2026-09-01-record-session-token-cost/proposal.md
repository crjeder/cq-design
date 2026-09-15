## Why

Real token cost is never recorded anywhere. `build/attempts.jsonl` stores
`prompt_chars` and `model`; `evals/run_evals.py` later *reconstructs* a cost
estimate as `(prompt_chars / 4) * input_price` (`run_evals.py:164`). That
estimate discards output tokens (often the larger half), cache read/creation
tokens (which dominate a multi-attempt loop), thinking tokens, and any
per-subagent breakdown -- so the eval scorecard's "cost/part USD" is a rough
proxy, and outside `evals/` no cost data is kept at all.

A running session cannot observe its own token usage -- no tool returns it
mid-loop. Real numbers exist in exactly two post-hoc places: the session
transcript JSONL (`message.usage` on every assistant turn, including
`isSidechain` builder-agent turns), and the `claude -p --output-format json`
result envelope (`usage`, `total_cost_usd`). Neither is captured today.

Recording real cost into every working directory -- not just eval runs -- means
any past run can be cost-post-evaluated later, and the eval scorecard can report
billed cost instead of a char-count guess.

## What Changes

- **[B] Session-cost record.** Add `src/session_cost.py` (stdlib only): given a
  transcript path, sum `message.usage` per model, split main vs. subagent
  (`isSidechain`), price it against `evals/model_prices.json`, and write a
  cumulative `build/cost.json` keyed by session id (so `--resume` keeps prior
  sessions). `src/init_permissions.py` seeds a `Stop` hook into the working
  directory's `.claude/settings.local.json` (the same file it already writes
  permission patterns to) that runs the recorder each turn; the hook is a no-op
  when `build/` does not exist, and always exits 0.
- **[E] Eval generation captures the envelope.** `run_evals.generate_case`
  switches its `claude -p` subprocess to `--output-format json`, captures
  stdout, and writes the `usage` / `total_cost_usd` / `num_turns` /
  `duration_ms` block to `<case>/cost.json`.
- **Scorecard prefers real cost.** `attempt_metrics` cost precedence becomes:
  `<case>/cost.json` (E envelope) -> `<case>/build/cost.json` (B combined) ->
  the `prompt_chars` estimate (unchanged fallback).
- **Price table gains output rates.** `evals/model_prices.json` entries become
  `{"input": <usd/MTok>, "output": <usd/MTok>}`; cache tokens are priced with
  documented approximate multipliers (read 0.1x input, creation 1.25x input).
  `run_evals.load_prices` and `attempt_metrics` are updated to the new shape.

## Capabilities

### New Capabilities
- `session-token-cost`: hook-driven transcript parse producing a cumulative
  `build/cost.json` per working directory.

### Modified Capabilities
- `eval-harness`: cost metric prefers a recorded billed cost over the
  `prompt_chars` estimate; `--generate` captures the `claude -p` result envelope.
- `skill-permission-bootstrap`: bootstrap also seeds the session-cost `Stop`
  hook, idempotently and non-destructively.

## Impact

- New `src/session_cost.py`; new `tests/test_session_cost.py` (fast, no CadQuery
  -- synthetic transcript fixture).
- `src/init_permissions.py` + `src/skill_permissions.json`: optional `hooks`
  block, merged like `allow`; hook command path resolved to the skill `src` dir
  at seed time. `tests/test_init_permissions.py`: hook-seeding cases.
- `evals/run_evals.py`: envelope capture in `generate_case`, real-cost
  precedence in `attempt_metrics` / `score_case`, new price-table shape in
  `load_prices`. `evals/model_prices.json`: restructured. `tests/test_run_evals.py`:
  precedence + new-shape cases.
- Docs: `CLAUDE.md` (script index + file layout + key constraints),
  `reference/scripts.md` (`session_cost.py` contract), `skill/phase4_deliver.md`
  (`build/cost.json` in the working-dir tree; not bundled into `lib/`),
  `skill/phase0_sourcing.md` / bootstrap output note.
- No change to `attempts.jsonl`, the `prompt_chars` field, the plan schema,
  exporters, or the JSON wrapper contract.
