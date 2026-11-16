## 1. Core module

- [x] 1.1 Create `src/pipeline.py` with the `MILESTONES` table (prerequisites, optional flag, route) from design D3 and a journal parser that applies the last-`phase0/restart` cut
- [x] 1.2 Implement order-based validity (D2): `done` / `void` with the unmet prerequisite, per-part milestones keyed by `<id>`, `design_approved` over all part ids read from `BUILD_PLAN.json`
- [x] 1.3 Implement part staleness (D4): parse `sha=` from `part_accepted` lines, compare to `freshness.script_hash`, unknown when absent
- [x] 1.4 Implement routes (D5): `design`, `plan` (terminal at `plan_approved`), stateless `edit` with `route_forbids`
- [x] 1.5 Implement CLI `status`, `can`, `advance` (D6): JSON output, `errors` shape `{type, message, hint}`, exit 0/1, `advance` appends via `log.append_line` and writes nothing on refusal

- [x] 1.6 Implement sourcing status (D9): `sourcing_skipped` milestone, `rung_<n>` parse, rung-3 shortcut to `delivered`, `skipped` phases
- [x] 1.7 Plan-then-design continuation (D10): `--route design` after a plan-route run lists the part loop

## 2. Tests

- [x] 2.1 `tests/test_pipeline.py`: every scenario in `specs/pipeline-state-machine/spec.md` (fresh dir, restart, re-approved dimensions, missing part, out-of-order script line, stale/legacy part, refused/valid/unknown advance, edit with empty dir, plan route complete)
- [x] 2.2 Test that `MILESTONES` keys match the milestone table in `skill/resume.md`
- [x] 2.3 Run `uv run pytest tests/test_pipeline.py tests/test_log.py` and `ruff check` / `ruff format` on the new files

## 3. Skill prose and prompts

- [x] 3.1 `skill/resume.md`: procedure steps 1-4 read `pipeline.py status` and resume at `allowed_next[0]`; document void and stale reporting; milestone table gains `sha=` on `part_accepted`
- [x] 3.2 `skill/phase*.md` and `SKILL.md`: user-decision milestone appends use `pipeline.py advance`; `part_accepted` passes `sha=`; script-written milestones unchanged
- [x] 3.3 `commands/design.md`, `plan.md`, `edit.md`: pass `--route` and state that the route is never inferred
- [x] 3.4 `src/render_prompt.py`: builder prompt gains the part id and allowed-steps line (spec "Sub-agent scope"); extend its test

## 4. Docs and bookkeeping

- [x] 4.1 `reference/scripts.md` contract entry for `pipeline.py`; `FILES.md` line; `ARCHITECTURE.md` mention
- [x] 4.2 `documentation/pipeline.md`: mark step 1 and the state-machine decision as implemented
- [x] 4.3 On completion move the "Pipeline state machine" and "LLM skipped the pipeline on an edit run" items from `TODO.md` to `documentation/DONE.md`
- [x] 4.4 Run the full suite `uv run pytest tests/` and fix regressions
