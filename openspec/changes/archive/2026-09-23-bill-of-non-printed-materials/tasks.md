## 1. Schema

- [x] 1.1 Add optional top-level `bom` array to `src/build_plan_schema.json` (row: required `item`, `parts` minItems 1; optional `spec`, `qty` integer >= 1, `note`; `additionalProperties: false`)
- [x] 1.2 Add optional `supplied_hardware` string to `src/blocks/inventory_schema.json`
- [x] 1.3 Set `supplied_hardware` on the seven blocks in design.md's table in `src/blocks/inventory.json`

## 2. plan.py

- [x] 2.1 Add `_check_bom_parts` (hard error for unknown part ids in `bom[].parts`) and call it from `validate_plan`
- [x] 2.2 Add `check_bom_coverage(plan, inventory_path)` advisory and print it in `_cmd_validate` as "BOM findings (N, advisory)"
- [x] 2.3 Render the **Non-printed hardware** table in `summarize` (omitted when `bom` is empty/absent)

## 3. Prompts and skill docs

- [x] 3.1 `prompts/planning.md`: narrow `planning_notes` category (c) to the assembly procedure; add a rule directing screws/nuts/washers, inserts, magnets, bearings, springs, filament/rod pins and adhesives into `bom`; add `bom` to the output JSON example
- [x] 3.2 `skill/phase4_deliver.md`: add a **Hardware to buy** item to the delivery report and the `README.md` contents list, rendered from `bom`
- [x] 3.3 Update `reference/scripts.md` for the new `plan.py validate` advisory section

## 4. Tests and cleanup

- [x] 4.1 `tests/test_plan.py`: valid row, unknown key, `qty: 0`, unknown part id, coverage finding present/absent, summary table present/omitted
- [x] 4.2 Inventory test: `heat_set_boss` has `supplied_hardware`, `fillet_box` does not
- [x] 4.3 Run `uv run pytest tests/test_plan.py tests/test_eval_corpus.py` and `ruff check`/`ruff format` on `src/plan.py`
- [x] 4.4 Tick the TODO.md item and replace its details section with a pointer to this change
