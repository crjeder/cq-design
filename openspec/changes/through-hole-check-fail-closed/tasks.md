## 1. Plan approval records b1

- [x] 1.1 `src/pipeline.py`: on `advance phase2/plan_approved`, append `b1=<part>:<n>,...` from `BUILD_PLAN.json` (CAD intent: every part, missing = 0; print: only parts declaring `through_count`; omit when none)
- [x] 1.2 `src/pipeline.py`: parse `b1=` from the latest valid `plan_approved` line; `status` reports `approved_b1`
- [x] 1.3 `tests/test_pipeline.py`: the three scenarios in `specs/pipeline-state-machine/spec.md`

## 2. Gate uses the approved b1 and fails closed under CAD

- [x] 2.1 `src/quality_gate.py`: `_through_hole_issues` takes `approved_b1` (int or None) and `cad` (bool); runs when `cad` or any interface declares `through_count`; missing = 0
- [x] 2.2 `src/quality_gate.py`: `run_gate` reads the approved b1 for the part from `build/journal.md` beside the plan (reuse `pipeline.py`'s reader); adds `approved_b1`/`plan_b1` and the "plan changed after approval" message when they differ
- [x] 2.3 `tests/test_quality_gate.py`: scenarios CAD-no-interfaces, plan-lowered-after-approval, standalone run; existing legacy-plan test switched to explicit print intent

## 3. Prompt rule for the fix route

- [x] 3.1 `skill/phase3_build.md` Quality gate: `through_hole_count_mismatch` is fixed in the part script; changing `through_count` means re-approving the plan (voids accepted parts)

## 4. CADGenBench runner

- [x] 4.1 `evals/cadgenbench_run.py` `build_prompt`: generation prompt starts with `/cq-design:design `
- [x] 4.2 `evals/cadgenbench_run.py`: post-generation audit writes `<fid>.pipeline` into `sanity.json` and prints the bypassed count
- [x] 4.3 `tests/test_cadgenbench_run.py`: prompt prefix, plan-less audit, full-pipeline audit, round-copy ignored

## 5. Single milestone writer

Found in the 5.3 run: fixture 150 wrote `plan_approved` with `log.py journal append`, so no
`b1=` was recorded and the gate fell back to the live plan.

- [x] 5.1 `src/log.py` `journal append` refuses `pipeline.MILESTONES` keys and names `pipeline.py advance`; `tests/test_log.py` covers the refusal and the `phase0/restart` path
- [x] 5.2 `skill/resume.md`, `reference/scripts.md` (`log.py`) and `README.md`: milestones go through `pipeline.py advance` only

## 6. Docs and check

- [x] 6.1 `reference/scripts.md` (`pipeline.py`, `quality_gate.py`) and `evals/README.md` (runner prompt, `sanity.json` shape)
- [x] 6.2 `uv run pytest tests/test_log.py tests/test_pipeline.py tests/test_quality_gate.py tests/test_cadgenbench_run.py tests/test_plan.py`
- [ ] 6.3 Re-run `evals/cadgenbench_run.py --fixtures 104,119,150` and confirm every fixture's `pipeline` block is all true; compare `cost.json` with the 2026-11-22 runs
