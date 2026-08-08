## 1. Gate becomes report-only (D1)

- [x] 1.1 `src/quality_gate.py`: change `run_gate`'s `allow_fix` default to `False`
- [x] 1.2 `src/quality_gate.py`: replace the `--no-fix` CLI flag with `--fix` and pass `allow_fix=args.fix`
- [x] 1.3 `src/quality_gate.py`: update the module docstring usage lines (drop `--no-fix`, show `--fix` as the opt-in)
- [x] 1.4 `tests/test_quality_gate.py`: add a case asserting a default `run_gate` on an erroring script leaves the script bytes unchanged and reports `fix_rounds: 0`
- [x] 1.5 Run `uv run pytest tests/test_quality_gate.py tests/test_gate_freshness.py tests/test_gate_plan_validation.py tests/test_keep_out_check.py tests/test_plate_clearance_check.py`

## 2. Route gate findings into the part loop (D2, D3)

- [x] 2.1 `skill/phase3_build.md` Quality gate section: state that the gate runs report-only and that `severity: error` findings re-enter Step 2's fix path with the finding's `type`/`message`/`hint`
- [x] 2.2 `skill/phase3_build.md` Quality gate section: bound gate-driven fix rounds at 2 per part, then escalate to the user
- [x] 2.3 `skill/phase3_build.md`: note that `--fix` exists for standalone use and is not used by the pipeline
- [x] 2.4 Mirror both edits into the installed skill copy

## 3. Coverage-first visual review (D4, D6)

- [x] 3.1 `reference/Visual Review Checklist.md` Rules section: add the coverage-first reporting rule (report every discrepancy with confidence and severity; the fix decision filters, not the review)
- [x] 3.2 `reference/Visual Review Checklist.md`: state that an advisory finding is reported but does not fail a question or consume a retry
- [x] 3.3 `skill/phase3_build.md` Implementation audit return contract: add `confidence` and `severity` to finding entries and allow non-failing entries
- [x] 3.4 `skill/phase3_build.md` Step 4 progressive branch: display advisory findings grouped separately from failed questions
- [x] 3.5 Mirror into the installed skill copy

## 4. Drop the builder self-check (D5)

- [x] 4.1 `skill/phase3_build.md` Step 4: delete the autonomous branch's light self-check and its "something obviously broken" retry sub-branch; a clean deterministic pass returns `status: passed`
- [x] 4.2 `skill/phase3_build.md`: update the Builder return contract prose describing what `status: passed` means
- [x] 4.3 `skill/phase3_build.md` Step 4 intro: drop the progressive-vs-autonomous "what counts as done" framing that only existed to introduce the self-check
- [x] 4.4 Mirror into the installed skill copy

## 5. Docs

- [x] 5.1 `CLAUDE.md`: update the `src/quality_gate.py` row (report-only default, `--fix` opt-in)
- [x] 5.2 `IMPROVEMENT_PLAN.md`: mark item 10 done, pointing at this change

## 6. Acceptance (eval sweep)

- [x] 6.1 Run `evals/run_evals.py --generate` on the full 10-case corpus into `evals/runs/c4-review-collapse/`
- [x] 6.2 Compare first-shot rate, attempts-to-pass, and cost per accepted part against `evals/runs/c2-prompt-chars/` and `evals/runs/c3-planning/`; revert if either regresses beyond the documented run-to-run spread
- [x] 6.3 Write the C4 result section into `CLAUDE5_CONVERSION_PLAN.md`, naming the run dir and the numbers, including any case the sweep failed to complete
