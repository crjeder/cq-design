## 1. Plan-validation stage

- [x] 1.1 Add `_run_plan_validation_stage(plan_path)` to `src/quality_gate.py`: call `plan_validate.validate_plan(plan_path)` and map each returned error string to `{source: "plan", severity: "error", type: "plan_invalid", message: <string>, hint: ...}`. Empty list in, empty list out.
- [x] 1.2 Import `validate_plan` locally inside the stage (mirroring how `_run_kinematic_stage` imports `run_kinematic_check`) so the gate's import surface is unchanged for callers that never validate.

## 2. Wire into run_gate with skip semantics

- [x] 2.1 In `run_gate`, after the fix loop and the 3MF check, call the plan-validation stage once (before the kinematic stage), append its issues to `all_issues`.
- [x] 2.2 Run the kinematic stage only when the plan-validation stage produced no error issue; on any `plan_invalid` error, skip the kinematic stage (and any other plan-consuming stage) so the raw-index path in `kinematic_check.py` is unreachable.
- [x] 2.3 Confirm `passed = not errors` still holds (the `plan_invalid` errors flow into the same `errors` filter) and the print recipe stays gated on `passed`.

## 3. Tests

- [x] 3.1 Malformed `axis_dir` (e.g. `"XY"`): gate report has a `plan_invalid` error, `passed` is false, and no traceback is raised.
- [x] 3.2 Missing `required_range` on a kinematics entry: same -- structured `plan_invalid`, kinematic stage skipped (assert the sweep was not invoked, e.g. monkeypatch `_run_kinematic_stage` to fail if called).
- [x] 3.3 Each validator error string maps to one `plan_invalid` issue (multi-error plan -> matching count).
- [x] 3.4 Valid plan: plan-validation contributes zero issues and the kinematic stage runs (regression guard that the report is unchanged).
- [x] 3.5 A plan with no kinematics still validates cleanly and gates normally.

## 4. Verification

- [x] 4.1 `uv run pytest tests/test_quality_gate.py tests/test_kinematic_check.py tests/test_plan_validate.py` pass.
- [x] 4.2 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on `src/quality_gate.py`.
- [x] 4.3 Update `CLAUDE.md` (`quality_gate.py` row mentions up-front plan validation) and the `quality_gate.py` module docstring's stage list; remove the corresponding `TODO.md` "Code review findings" line.
