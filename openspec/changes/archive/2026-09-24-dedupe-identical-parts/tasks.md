## 1. Schema and validation

- [x] 1.1 Add `copy_of` to the part definition in `src/build_plan_schema.json`
- [x] 1.2 Add `units.is_copy(part)` helper and copy-reference checks in `src/plan.py` validate (missing, self, chained, source with `unions`)
- [x] 1.3 Tests in `tests/test_plan.py` for each scenario in `specs/part-copies/spec.md`

## 2. Export

- [x] 2.1 In `src/model_export.py`, build copy unions from the source's authored geometry (mirror then pose); skip script load for copies
- [x] 2.2 Make `freshness.py` key a copy's manifest entry to the source script hash
- [x] 2.3 Route `quality_gate.py`, `render_prompt.py`, `build_template.py` script enumeration through `is_copy`
- [x] 2.4 Export/freshness tests (CadQuery) for mirrored copy bbox, identical translated copy, and stale-source case

## 3. Prompts and docs

- [x] 3.1 Add the `copy_of` rule to `prompts/planning.md` (pairwise-mirrored or identical parts; no emboss/text on mirrored copies)
- [x] 3.2 Note copy parts are skipped in `skill/phase3_build.md`; document the field in `reference/scripts.md`
- [x] 3.3 Mark "Deduplicate pairwise-mirrored parts" done in `TODO.md`
