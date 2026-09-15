## 1. Wrapper: split the OCC hint table into typed errors

- [x] 1.1 `src/run_cadquery_model.py`: change `_OCC_HINTS` values from `hint: str`
      to `(type, hint)` pairs for the six known classes
- [x] 1.2 `_translate_stderr`: emit the matched entry's `type` instead of the
      literal `"occ_exception"` string; keep `occ_class` and the unmapped
      fallback (`type: "occ_exception"`, generic hint) unchanged
- [x] 1.3 `tests/test_run_wrapper.py`: update existing OCC-class assertions to
      also check `type`; add one case per new type (six) and confirm an
      unmapped class (e.g. `Standard_DomainError`) still returns `occ_exception`

## 2. Downstream severity and docs

- [x] 2.1 `src/quality_gate.py`: add the six new types to the `severity: "error"`
      tuple alongside `occ_exception`
- [x] 2.2 `tests/test_quality_gate.py`: add a case asserting one new type (e.g.
      `command_not_done`) classifies as `severity: error`
- [x] 2.3 `skill/phase3_build.md`: add the six new types to the blocking-error-
      types line
- [x] 2.4 Mirror 2.3 into the installed skill copy if one exists
- [x] 2.5 `SKILL.md`: replace the single `occ_exception` error-table row with
      six rows (new type, one-line hint summary) plus the unmapped-fallback row

## 3. Docs

- [x] 3.1 `IMPROVEMENT_PLAN.md`: mark item 9 done, pointing at this change,
      noting no telemetry existed to prioritize by frequency so this operationalizes
      the existing six-class table rather than adding new signatures

## 4. Verify

- [x] 4.1 `uv run pytest tests/test_run_wrapper.py tests/test_quality_gate.py`
