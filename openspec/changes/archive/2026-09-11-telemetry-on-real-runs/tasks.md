## 1. telemetry.py: fold helper and hook entry point

- [x] 1.1 Add `fold_attempts(records: list[dict]) -> list[dict]`: group by
      `(part_id, attempt)`, return one record per group (last in input order),
      preserving the order of first appearance for the groups themselves.
- [x] 1.2 Add a `--hook` CLI mode: read a `PostToolUse` payload from stdin,
      no-op (exit 0, write nothing) unless the tool call is a Bash/PowerShell
      invocation matching the `run_cadquery_model.py` shape already
      allowlisted in `skill_permissions.json`.
- [x] 1.3 In hook mode, parse `part_id` from the command's `--script
      build/<part_id>.py` argument; no-op if it can't be parsed or
      `build/attempts.jsonl`'s parent directory doesn't exist.
- [x] 1.4 Compute `attempt` as `len(fold_attempts(existing records with this
      part_id)) + 1`.
- [x] 1.5 Derive `outcome` (`"pass"` if the tool result JSON has
      `success: true`, else `"fail"`) and `error_types` (the `type` of each
      entry in the result's `errors` list) from the tool result.
- [x] 1.6 Read `model` from the hook payload; read `prompt_chars` from
      `build/<part_id>_prompt_attempt<n>.txt` when it exists at the computed
      `attempt` number, else omit the field.
- [x] 1.7 Set `visual_review: null`, validate the assembled record with the
      existing `validate_attempt`, and append via the existing single-line
      append path. On any validation failure, exit 0 and write nothing
      (fail-open, matching `session_cost.py --hook`).

## 2. Hook wiring

- [x] 2.1 Add a `PostToolUse` entry to the canonical hooks block in
      `src/skill_permissions.json`, matching the `run_cadquery_model.py`
      command shape, invoking `python "{telemetry_path}" --hook`.
- [x] 2.2 Extend `init_permissions.py`'s `_resolved_hooks`/path substitution
      to also resolve `{telemetry_path}` (absolute path to `src/telemetry.py`),
      alongside the existing `{session_cost_path}`.
- [x] 2.3 Confirm `merge_hooks` seeds the new `PostToolUse` entry additively
      into an existing `.claude/settings.local.json` that already has the
      `Stop` hook, without duplicating or removing it.

## 3. Consumers fold before scoring

- [x] 3.1 `src/quality_gate.py._run_telemetry_stage`: fold the parsed records
      with `telemetry.fold_attempts` before checking for
      absent/empty/unparseable.
- [x] 3.2 `evals/run_evals.py` (`read_attempts` or wherever `attempts.jsonl`
      is parsed for `attempt_metrics`): same fold, applied before computing
      `first_shot_rate`, `mean_attempts_to_pass`, and the `prompt_chars`-based
      cost estimate.

## 4. Skill prose

- [x] 4.1 Rewrite `skill/phase3_build.md` Step 5 to the conditional
      follow-up-only form: append a record only when visual review ran and
      failed this attempt (`outcome=fail`, `error_types=["visual_mismatch"]`,
      `visual_review={...}`); otherwise state explicitly there is nothing to
      do.
- [x] 4.2 Update the "Telemetry append safety" note: the hook and Step 5 now
      both write, at disjoint times within one attempt (hook right after the
      wrapper call, Step 5's follow-up only after visual review) — no
      concurrent-write change versus the existing sequential-builders
      assumption.
- [x] 4.3 Remove the now-inaccurate "Skipping this step loses the measurement
      baseline" line (skipping the new Step 5 only loses the visual-mismatch
      detail, not the whole record) and replace with the accurate,
      smaller-consequence statement.

## 5. Tests

- [x] 5.1 `tests/test_telemetry.py`: `fold_attempts` — empty input, single
      record, two records same key (last wins), interleaved keys preserve
      first-appearance order for distinct groups.
- [x] 5.2 `tests/test_telemetry.py`: `--hook` — valid `run_cadquery_model.py`
      payload appends the expected record; non-matching command is a no-op;
      missing `build/` is a no-op; malformed payload exits 0 without writing.
- [x] 5.3 `tests/test_quality_gate.py`: telemetry stage no longer warns on a
      log holding a base+follow-up pair for the same `(part_id, attempt)`.
- [x] 5.4 `tests/test_run_evals.py`: `attempt_metrics`/scoring treats a
      base+follow-up pair as one attempt with the follow-up's `outcome`.

## 6. Verification

- [x] 6.1 Run the full suite (`uv run pytest tests/`) — green.
- [x] 6.2 Run `uv run python evals/run_evals.py` (score-only) against an
      existing run directory (e.g. `evals/runs/c7-hooks-on`) — aggregate
      metrics unchanged (fold is a no-op on single-line-per-attempt logs).
- [x] 6.3 Update `CLAUDE.md`'s `src/telemetry.py` one-liner and
      `reference/scripts.md`'s telemetry contract section to mention
      `fold_attempts` and `--hook`.
