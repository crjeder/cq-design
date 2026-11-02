## 1. Checked import

- [x] 1.1 Add `src/blocks/imported.py` with `import_solid(path, max_volume_deviation=0.01)`: extension dispatch (`.step`/`.stp` -> `importStep`, `.brep` -> `Shape.importBrep`, else `ValueError`) and the cheap check (BRepCheck plus faces under 1e-3 mm²)
- [x] 1.2 Implement the cumulative repair ladder (drop slivers + sew 1e-2, defeature flagged faces, MakeFilling patch + sew 1e-2) with the check after each rung. Add a `ponytail:` comment on the uncached per-run repair cost
- [x] 1.3 Enforce the volume limit against the imported volume; raise the `[cq-verify:step_unrepairable:<name>]` RuntimeError with the remaining statuses and the last volume delta
- [x] 1.4 Print the `[cq-design:step-repair] {json}` line on a successful repair
- [x] 1.5 Export `import_solid` from `blocks/__init__.py` and list it in the module docstring

## 2. Wrapper integration

- [x] 2.1 Add `step_unrepairable` to `_VERIFY_HINTS` in `src/run_cadquery_model.py`
- [x] 2.2 In `src/run_model_shim.py`, run BRepCheck per result body (skipping `keep_out`) and write `brep_check.json` keyed by union id/stem, using the grader's `"<Face|Edge|Vertex>: <status>"` format
- [x] 2.3 In `src/run_cadquery_model.py`, read `brep_check.json` and add one blocking `invalid_brep` error per failing body (de-duplicated statuses, per-union attribution, `success: false` regardless of `--strict`). Do nothing when the file is absent

## 3. Tests

- [x] 3.1 Test `import_solid`: a valid STEP box round-trips unchanged and prints nothing; an `.stl` path raises `ValueError`
- [x] 3.2 Test the repair path on a synthetic invalid solid (for example, a box with a zero-area sliver face built via ReShape/sewing): rung 1 repairs it and the repair line is printed. A tiny `max_volume_deviation` raises `step_unrepairable`
- [x] 3.3 Test the wrapper: a valid script has no `invalid_brep`; an invalid result body (constructed in the test script) gives `success: false` and one `invalid_brep`; a multi-union result attributes it to the right union; a `step_unrepairable` marker maps to the typed error
- [x] 3.4 Run the full suite (`uv run pytest tests/`) and the eval cases. Fix or record every case newly failing on `invalid_brep`

## 4. Prompts and docs

- [x] 4.1 `commands/edit.md`: both scripts use `from blocks import import_solid` / `result = import_solid(r"<abs path>")`. On `step_unrepairable`, stop and deliver nothing. Quote the repair line in the report
- [x] 4.2 `skill/phase0_sourcing.md`: rung-2 STEP/BREP imports use `blocks.import_solid`; `step_unrepairable` drops the candidate to the next rung
- [x] 4.3 `reference/scripts.md`: document `invalid_brep`, `step_unrepairable`, `brep_check.json` and the repair stdout line. Add `blocks/imported.py` to `FILES.md`
- [x] 4.4 Confirm `bundle_project.py` ships the new module (`blocks` is a bundled package) and `run_model_shim.py`

## 5. Benchmark verification

- [x] 5.1 Run `import_solid` on CADGenBench 202/217/240/250 `input.step`: 217 and 250 repair and their exported STEP passes `sanity_check_submission.py`; 202 and 240 raise `step_unrepairable` or report a patch repair
- [ ] 5.2 Re-run `evals/cadgenbench_run.py --fixtures 202,217,240,250 --force` and record the gate results
