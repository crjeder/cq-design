## Context

`attempts.jsonl` is written today by one path only: `skill/phase3_build.md`
Step 5, a prose instruction telling the orchestrating Claude to shell out to
`telemetry.py append` with six hand-assembled fields, "always, before
retrying or advancing." In the eval harness this is reliable because
`evals/run_evals.py --generate` drives a short, scripted session. In real
projects it is not: the 2026-09-08 C5 session ran 10 correction rounds over
two part scripts, and `quality_gate.py`'s advisory telemetry check reported
`No attempt telemetry found` twice — Step 5 was never reached, buried as one
step among many in an 80 KB per-part instruction file, in a session already
carrying plan edits, hand-rolled script fixes, and multiple `AskUserQuestion`
detours. The check that would have caught this is a `warning`, not a gate
failure (correctly — geometry is unaffected by missing telemetry), so
nothing forced a retry.

The existing `session-token-cost` capability already solves an equivalent
reliability problem the same way: `session_cost.py --hook` runs as a `Stop`
hook seeded by `init_permissions.py`/`skill_permissions.json`, independent of
whether the orchestrator remembers to call it. `build/cost.json` has never
been observed missing for a session that reached `build/`. This design
applies the same pattern to the fields of a telemetry record that don't
require an LLM's judgment.

## Goals / Non-Goals

**Goals:**
- The fields derivable from the wrapper's own JSON output (`part_id`,
  `attempt`, `outcome`, `error_types`, `prompt_chars`, `model`) are written
  every time `run_cadquery_model.py` runs, with no dependency on the
  orchestrator remembering a separate step.
- The append-only, never-rewrite invariant on `attempts.jsonl`
  (`attempt-telemetry` Requirement: Append-only log semantics) is preserved
  unchanged.
- `visual_review`, which only Claude's own judgment can produce, keeps being
  written by the orchestrator — but as a small, single-purpose follow-up
  call, not as one field among six in a record it must otherwise assemble
  correctly from memory.
- Existing consumers (`quality_gate.py`'s telemetry-missing check,
  `run_evals.py`'s scoring) keep working against a log that may now contain
  two lines for one logical attempt.

**Non-Goals:**
- Not attempting to make the hook capture `visual_review` itself (it has no
  access to the rendered preview images Claude judges).
- Not changing `outcome`'s semantics (pass only when Step 4 accepted the
  part) — a hook-written base record's `outcome` reflects geometry validation
  only; a failed visual review still overrides it via the follow-up record.
- Not parallelizing builders or addressing concurrent-append safety beyond
  what already holds (sequential builders, per the Agent routing gate).
- Not touching `session-token-cost` itself.

## Decisions

**D1: `PostToolUse` hook on `run_cadquery_model.py`, not a wrapper-internal write.**
The wrapper subprocess runs in `tempfile.mkdtemp()` and knows nothing about
`build/attempts.jsonl`'s location or the orchestrator's `part_id`/`attempt`
bookkeeping (`CLAUDE.md`: "STL hidden during iteration... scripts run in
tempfile.mkdtemp()"). A `PostToolUse` hook instead observes the *Bash tool
call* Claude already makes every attempt — same trigger reliability as
`session_cost.py`'s `Stop` hook, without changing the wrapper's process
isolation or JSON contract. Alternative considered: have
`run_cadquery_model.py` accept `--attempts-log` directly and append inline.
Rejected because the wrapper does not know `attempt` (it has no state across
invocations) and adding that bookkeeping duplicates what the hook can derive
by reading the existing log.

**D2: `attempt` is computed by counting existing lines for that `part_id`.**
The hook reads `build/attempts.jsonl`, counts records (pre-dedupe, i.e. raw
line count) whose `part_id` matches the one parsed from the Bash command's
`--script build/<part_id>.py` argument, and uses `count + 1`. This mirrors
what Step 5 does today by hand and needs no new state file. Edge case: a
follow-up visual-review record for attempt N increments the count, so a
naive next-attempt hook call would misnumber attempt N+1 as N+2. Mitigated by
D4 (fold before counting: only count distinct `(part_id, attempt)` pairs).

**D3: `model` and `prompt_chars` come from data already available to the hook.**
`model` is available in the `PostToolUse` payload (the session's active
model, same source `session_cost.py` already reads for its per-model
breakdown). `prompt_chars` is read from
`build/<part_id>_prompt_attempt<n>.txt` (Step 1 already writes this before
the wrapper runs) when present, else omitted — degrading to
`quality_gate.py`'s existing "missing telemetry" advisory only for that one
field's cost-estimation use, never a hard failure.

**D4: Two lines per attempt, folded by `(part_id, attempt)` at read time, last wins.**
Rejected in-place rewriting of the base line once `visual_review` is known
(violates `attempt-telemetry`'s "SHALL never truncate, rewrite, or reorder
existing lines"). Instead the follow-up is a normal append: same `part_id`
and `attempt`, `outcome: "fail"`, `error_types: ["visual_mismatch"]`,
`visual_review` populated. Every reader that currently assumes one line per
attempt (`quality_gate._run_telemetry_stage`, `run_evals.read_attempts`)
gains a fold step: group by `(part_id, attempt)`, keep the last line in file
order. This is a small, shared, testable helper (`telemetry.py`'s new
`fold_attempts(records) -> list[dict]`), not duplicated logic.

**D5: Step 5 shrinks to a conditional single-purpose call.**
New Step 5: "if visual review ran this attempt and failed, append one record
via `telemetry.py append` with `outcome=fail`,
`error_types=["visual_mismatch"]`, `visual_review={...}`. Otherwise: nothing
to do — the hook's record already stands." This cuts the LLM-authored
surface from six fields assembled from four different sources down to one
conditional three-field call fired only on the less common path (a part that
passed geometry validation but failed the visual check), lowering both the
chance of the step being skipped and the cost of skipping it (the hook's
record, if the follow-up is missed, still correctly shows the part
eventually passed geometry — just not that a visual retry happened, a
smaller loss than the previous total gap).

## Risks / Trade-offs

- [Hook fires on every `run_cadquery_model.py` call, including exploratory
  runs outside the part loop (e.g. a manual debug invocation)] → Mitigation:
  scope the `PostToolUse` matcher to the same command shape
  `skill_permissions.json` already allowlists
  (`uv run --project * python * run_cadquery_model.py *`), and skip silently
  when `build/attempts.jsonl`'s directory doesn't exist yet or the command
  lacks a recognizable `--script build/<part_id>.py` argument — same
  no-op-when-not-applicable contract as `session_cost.py --hook`.
- [`attempt` miscounted if the hook and Step 5's follow-up ever race] →
  Mitigation: unaffected in practice (hook writes synchronously in
  `PostToolUse`, before the next tool call; Step 5's follow-up, if any, is a
  later Bash call in the same sequential turn — no concurrent writers, per
  the existing "Telemetry append safety" note).
- [A `PostToolUse` hook that mis-parses the command and appends a garbage
  record] → Mitigation: reuse `telemetry.py`'s existing `validate_attempt`
  before writing; on a parse failure the hook exits 0 and writes nothing
  (same fail-open contract as `session_cost.py`), never a partial line.
- [Consumers that fold by `(part_id, attempt)` but forget to apply the fold
  in a new call site regress to double-counting] → Mitigation: `fold_attempts`
  lives in `telemetry.py` as the one shared helper; `_run_telemetry_stage`
  and `read_attempts` both import it rather than re-deriving grouping logic.

## Migration Plan

1. Add `fold_attempts` to `src/telemetry.py`, plus the `--hook` entry point.
2. Wire the `PostToolUse` hook into `skill_permissions.json` /
   `init_permissions.py` (additive; existing installs pick it up next
   `init_permissions.py` seed, same as any other hook change).
3. Update `quality_gate.py._run_telemetry_stage` and
   `evals/run_evals.py.read_attempts` to fold before scoring.
4. Rewrite `skill/phase3_build.md` Step 5.
5. No data migration: existing `attempts.jsonl` files (eval runs) already
   have one line per attempt, which folds to itself (no-op).

Rollback: remove the `PostToolUse` hook entry and revert Step 5's prose;
`fold_attempts` is a no-op on files with no duplicate `(part_id, attempt)`
keys, so it is safe to leave in place independent of the hook.

## Open Questions

- Should the hook also fire after `quality_gate.py` to fold in gate-level
  `error_types` (e.g. `overhang_exceeded`) that the wrapper alone can't see?
  Left out of this change's scope — the wrapper's own `errors` already cover
  the failure types Step 5 currently logs; extending to gate findings is a
  natural follow-up once the base mechanism is proven on real sessions.
