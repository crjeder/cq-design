## 1. Schema and validation

- [x] 1.1 Add `parts[].probes` to `src/build_plan_schema.json`: array of `oneOf` branches keyed on `kind` (`solid_at`/`empty_at`, `ray`, `bbox`), each `additionalProperties: false`, `label` required (minLength 1), optional `instance`; no `delta` branch
- [x] 1.2 Extend `plan._check_instances` in `src/plan.py` so a probe `instance` must name a `blocks_needed` id of the same part (same message form as the interface check)
- [x] 1.3 Tests in `tests/test_plan.py`: plan with authored probes validates; absent `probes` validates; missing `label`, `ray` without `hits`, `kind: "delta"`, and an unknown field each fail; unknown probe `instance` fails naming part and id

## 2. Registry seeding

- [x] 2.1 In `src/probes.py` `plan_probes()`, append each `part["probes"]` entry as `Probe(**entry)` with list fields converted to tuples, after the interface-derived probes
- [x] 2.2 Update the `probes.py` module docstring to mention authored plan probes
- [x] 2.3 Test (CadQuery): an authored `empty_at` probe with no instance fails the final registry check on a solid box and passes on the same box with a hole at that point; an authored probe with an `instance` is skipped until that instance is armed
- [x] 2.4 Test: changing an authored probe's point changes the `Part` step key

## 3. Planner prompt

- [x] 3.1 Add rule 17 to `prompts/planning.md`: request dimensions that no positioned, sized interface covers become labelled authored probes in build pose; walls and step heights as a `solid_at`/`empty_at` bracket; points at least 0.1 mm off any surface
- [x] 3.2 Add a `probes` example to the required-output-schema example in `prompts/planning.md`
- [x] 3.3 Test that the rendered planning prompt contains the probe rule and the bracket example (extend the existing prompt-render test)

## 4. Docs and checks

- [x] 4.1 Document authored probes in the `src/probes.py` row of `reference/scripts.md`
- [x] 4.2 Run `uv run pytest tests/test_plan.py` plus the probe/part tests touched; run `ruff check --fix` and `ruff format` on changed Python files
- [x] 4.3 `openspec validate plan-authored-probes`
