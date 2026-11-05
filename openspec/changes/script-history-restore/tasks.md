## 1. Script history module (`src/script_history.py`)

- [x] 1.1 `record_run(script, ok, *, attempt=None, suppressed=None)`: blob `build/history/<stem>/<sha12>.py` if absent, `run` event in `log.jsonl`; honour `CQ_HISTORY_SKIP`; swallow failures with a one-line stderr warning
- [x] 1.2 Target resolution: `@last_ok`, `@prev`, `@<prefix>` (>= 4 hex, unique), mark names; errors for missing / ambiguous / unknown
- [x] 1.3 CLI `restore <target> <script>` (rewrite, `restore` event, step-worker `restore` event in `<stem>.steps.jsonl` when present, `attempt_mismatch` warning) and `mark <name> <script>` (reject `@` names); one JSON object out
- [x] 1.4 `tests/test_script_history.py` (stdlib only, no CadQuery): blob dedupe, each target, ambiguous prefix, mark/restore, attempt mismatch, unwritable dir, steps.jsonl restore event

## 2. Recording in the run tools

- [x] 2.1 `src/run_cadquery_model.py`: call `record_run` once per run with `success` and the plan revision when the script's stem is a plan part
- [x] 2.2 `src/step_worker.py`: call `record_run` per run (ok = steps passed and full tier ok), set `CQ_HISTORY_SKIP=1` on the full-tier subprocess, same for the fallback path
- [x] 2.3 Tests: one event per step-worker run including full tier and fallback (`tests/test_step_worker.py`); edit-style raw script recorded (`tests/test_run_wrapper.py`)

## 3. Run-time suppression (`src/blocks/part.py`, `src/step_worker.py`)

- [x] 3.1 `run --suppress <id>` (repeatable) sets `CQ_SUPPRESS` for warm and fallback runs
- [x] 3.2 `Part` reads `CQ_SUPPRESS`; suppressed `select` / `resize` / `place` record `suppressed: true` and skip `_chain`, construction, boolean, probes, arming; unknown id is a `step_plan` error
- [x] 3.3 Report `suppressed: [ids]`, skip the full tier, record `suppressed` in history
- [x] 3.4 Tests in `tests/test_step_part.py` / `tests/test_step_worker.py`: script unchanged, downstream `cut removed no volume`, plan probe fails at `result()`, toggle cache-warm, cold run ignores the env var

## 4. Gate delta (`src/quality_gate.py`)

- [x] 4.1 `--previous <report>`: `delta.resolved` / `delta.regressed` over `(type, union, source)` of `fix` / `re_export` findings; no `delta` without the flag; unreadable file exits 1 naming the path
- [x] 4.2 Tests in `tests/test_quality_gate.py` on synthetic report dicts

## 5. Instructions

- [x] 5.1 `skill/phase3_build.md`: `script_history.py mark accepted` at acceptance and accept-as-is; gate loop passes `--previous`, restores `accepted` on empty `resolved` or non-empty `regressed`, re-marks on progress, re-exports and re-gates from `accepted` after a reverted final round; resume message says the edit was reverted and why
- [x] 5.2 `prompts/builder.md`: undo with `script_history.py restore @prev | @last_ok | <mark>`, never by hand-reverting; `--suppress <id>` to test a feature, never on the final run; "previous edit reverted" means take a different approach
- [x] 5.3 `commands/edit.md` step 4/5: restore `@prev` when a revision breaks a successful run or a passing diff check
- [x] 5.4 Check `src/render_prompt.py` builder output renders the new commands (scenario "Builder prompt names restore")

## 6. Wiring and docs

- [x] 6.1 `src/skill_permissions.json`: allow `script_history.py` in both path forms, like `step_worker.py`
- [x] 6.2 `reference/scripts.md` entries for `script_history.py`, and updates for `step_worker.py` (`--suppress`, recording), `run_cadquery_model.py` (recording), `quality_gate.py` (`--previous`, `delta`); `FILES.md` line for the new script and test
- [x] 6.3 Confirm `bundle_project.py` does not bundle `script_history.py` (`run_cadquery_model.py` is not bundled either)
- [x] 6.4 `uv run pytest tests/test_script_history.py tests/test_step_worker.py tests/test_step_part.py tests/test_quality_gate.py tests/test_run_wrapper.py`; `ruff check --fix` and `ruff format` on changed files
