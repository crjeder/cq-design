## Why

`build/attempts.jsonl` is the baseline every prompt/reference/model-routing
change is judged against, but it is only ever written by a prose-instructed
Step 5 in `skill/phase3_build.md` (80 KB, read once per part) that the
orchestrating Claude must remember to run after every attempt, inside long
autonomous sessions. It silently fails: the 2026-09-08 C5 Phone-Holder
session (a 10-round real project) reports `"No attempt telemetry found at
...\build\attempts.jsonl"` from `quality_gate.py` twice, and the finding is
only ever an advisory `warning` — nothing fails the run or forces a fix.
Every eval scorecard on file is from `evals/runs/` (the harness, which does
call Step 5 faithfully); zero real project directories have contributed
telemetry. There is currently no way to tell whether skill changes are
helping or hurting actual use.

## What Changes

- Add a `PostToolUse` hook (seeded the same additive/idempotent way
  `session_cost.py`'s `Stop` hook already is, via `init_permissions.py` /
  `skill_permissions.json`) that fires after every `run_cadquery_model.py`
  invocation and appends the base per-attempt telemetry record itself:
  `part_id`, `attempt` (computed from existing log lines for that
  `part_id`), `outcome` and `error_types` (derived from the wrapper's own
  JSON), `prompt_chars` (read from the Step 1 prompt file when present), and
  `model`. `visual_review` is written `null` — the hook runs before Step 4's
  visual judgment exists.
- Step 5 in `skill/phase3_build.md` is reduced: it no longer assembles or
  writes the full record. It only appends a second, smaller follow-up record
  (`outcome: "fail"`, `error_types: ["visual_mismatch"]`, `visual_review`
  populated) for the same `part_id`/`attempt`, and only when visual review
  ran and failed. When review passed or did not run, there is nothing to do
  — the hook's record already stands and is correct.
- `attempts.jsonl` scoring (`run_evals.py` and `quality_gate.py`'s
  `_run_telemetry_stage`) treats two records sharing the same `part_id` +
  `attempt` as one logical attempt, with the **last** line winning — the
  append-only, never-rewrite invariant is unchanged; this is a read-side
  fold, not a write-side mutation.
- `src/telemetry.py` gains a hook-mode entry point (`--hook`, reading a
  Claude Code `PostToolUse` payload from stdin) alongside the existing
  `append` CLI, mirroring `session_cost.py`'s `--hook` pattern.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `attempt-telemetry`: the per-attempt record is written automatically by a
  `PostToolUse` hook for the geometry-derived fields, not solely by the
  orchestrator's Step 5 CLI call; a `part_id`+`attempt` pair may now appear
  as two append-only lines (base + visual-review follow-up), and consumers
  fold them by taking the last line per key instead of assuming one line per
  attempt.
- `eval-harness`: `read_attempts` (or equivalent) dedupes `attempts.jsonl` by
  `(part_id, attempt)`, keeping the last record, before computing
  `first_shot_rate` / `mean_attempts_to_pass`.

## Impact

- `src/telemetry.py`: new `--hook` entry point; record-shape/dedupe helper
  usable by both the hook and `run_evals.py`.
- `src/init_permissions.py`, `src/skill_permissions.json`: add the
  `PostToolUse` hook entry (additive, same merge path as the existing `Stop`
  hook).
- `src/quality_gate.py` (`_run_telemetry_stage`): fold by `(part_id,
  attempt)` before checking for an empty/unparseable log.
- `evals/run_evals.py` (`read_attempts`/`attempt_metrics`): same fold.
- `skill/phase3_build.md`: Step 5 rewritten to the smaller follow-up-only
  form; "Telemetry append safety" note updated (still sequential builders,
  now also a hook writer — no concurrent-write change since the hook and
  Step 5 write at disjoint times per attempt).
- Tests: `tests/test_telemetry.py`, `tests/test_run_evals.py`, a new test for
  the hook entry point, `tests/test_quality_gate.py` (telemetry stage fold).
