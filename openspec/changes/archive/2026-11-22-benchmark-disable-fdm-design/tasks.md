## 1. Schema and plumbing

- [x] 1.1 Add optional `design_intent` enum to `src/printer_profile_schema.json` and `src/build_plan_schema.json`; test valid, invalid and absent in `tests/test_plan.py`
- [x] 1.2 Planner copies the profile's `design_intent` into the plan (`src/render_prompt.py` / `skill/phase2_planning.md`); `src/plan.py` validates it

## 2. Planning prompt

- [x] 2.1 Gate the print-only rules on `design_intent` (done in `render_prompt.py`: a note replaces the FDM guidelines and clearance table; `prompts/planning.md` unchanged)
- [x] 2.2 `src/render_prompt.py` omits those sections for `"cad"`; test that `"print"`/absent output is unchanged and `"cad"` contains none of them

## 3. Quality gate

- [x] 3.1 In `src/quality_gate.py` skip min-wall, thin-region, overhang, bridge, sliver and fin stages when the plan's `design_intent` is `"cad"`
- [x] 3.2 Gate tests: overhang finding dropped under `"cad"`, kept under `"print"`; wrapper gets no `--wall-min` under `"cad"`

## 4. Build

- [x] 4.1 `src/build_template.py` (and the bundled `build/build.py`) applies identity orientation for `"cad"`; skip `print_orientation` entirely
- [x] 4.2 Build test: tipped-by-default part delivers a STEP whose bbox equals the build-pose bbox under `"cad"`
- [x] 4.3 `cq-design:edit` never runs the gate or print orientation (commands/edit.md); nothing to change

## 5. Benchmark runner

- [x] 5.1 `evals/cadgenbench_run.py` seeds `profile.json` with `design_intent: "cad"` per fixture; trim `FIDELITY` to single solid, drawing authoritative
- [x] 5.2 Update `tests/test_cadgenbench_run.py` for the seeded profile and the shorter prompt

## 6. Docs

- [x] 6.1 Update `reference/scripts.md`, `evals/README.md`, `skill/phase2_planning.md` and `FILES.md` (if a file is added); run `uv run pytest tests/`
