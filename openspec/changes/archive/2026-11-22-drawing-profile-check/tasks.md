## 1. Gate stage

- [x] 1.1 Extract the build-pose body loader from `_run_oracle_stage` in `src/quality_gate.py` into one helper (part entry + script path -> compound of union vals) and use it there
- [x] 1.2 Add `_run_plan_probes_stage(plan, script_path)`: skip when the part has no `probes[]`; drop labels bound in the part's `acceptance_bindings[].probes`; evaluate the rest with `probes.evaluate(Probe(**entry), body)` (lists as tuples, as `plan_probes` does); emit `probe_unmet` errors (`source: "geometry"`, `label`, `kind`, `expected`, `observed`, `message`, `hint`)
- [x] 1.3 Call it in `run_gate` next to `_run_oracle_stage`
- [x] 1.4 Add `tests/test_quality_gate_plan_probes.py` cases with a plain part script: an inward-offset wall fails its `solid_at` with the right label/expected/observed, a matching body passes, an oracle-bound failing label is not reported, a part without `probes[]` emits nothing

## 2. Planning prompt

- [x] 2.1 Add the thin-wall / sheet-metal section-view paragraph to rule 17 in `prompts/planning.md`: reference face and material side per thickness dimension, bend radius side, flange direction, recorded in `planning_notes`; a `solid_at`/`empty_at` bracket per dimensioned wall face (points half the thickness from the face, at least 0.1 mm) and a flange-tip `solid_at`, labels naming the view

## 3. CADGenBench runner

- [x] 3.1 In `evals/cadgenbench_run.py` `generate()`, after `run_fixture` (also on timeout or error), `shutil.rmtree(work / ".venv", ignore_errors=True)`; update the module docstring
- [x] 3.2 Add a `tests/test_cadgenbench_run.py` case (stub `run_fixture`) asserting `.venv/` is gone and other files in the work dir remain

## 4. Docs and checks

- [x] 4.1 Document `probe_unmet` in the `quality_gate.py` entry of `reference/scripts.md`, and note in the `probes.py` entry that the gate now evaluates authored probes for every script kind
- [x] 4.2 Note the kept work directory (venv pruned) in the runner row of `evals/README.md`
- [x] 4.3 Run `uv run pytest tests/test_quality_gate.py tests/test_quality_gate_oracle.py tests/test_cadgenbench_run.py tests/test_plan.py` and `ruff check`/`ruff format` on changed files
