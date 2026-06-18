## 1. Schema and Validator

- [x] 1.1 Remove `print_orientation` from `build_plan_schema.json` required fields and properties for part objects
- [x] 1.2 Add `planning_notes` (string, optional) to `build_plan_schema.json` top-level properties
- [x] 1.3 Add `part_notes` (string, optional) to part object properties in `build_plan_schema.json`
- [x] 1.4 Add `clearance_mm` (number, optional) to interface object properties in `build_plan_schema.json`
- [x] 1.5 Remove `print_orientation` from the required-field list in `plan_validate.py` `_manual_check`

## 2. Orchestrator

- [x] 2.1 Remove the `"{{PRINT_ORIENTATION}}"` key-value pair from the `replacements` dict in `orchestrate.py` `_render_part_prompt`

## 3. Prompt Templates

- [x] 3.1 Rewrite `prompts/planning.md`: add coordinate vocabulary table, planning_notes/part_notes instructions, fit-type clearance table with interactive-ask fallback, dimension -1 placeholder rule, single-part assembly-omit rule, and update schema example to remove `print_orientation` and add new optional fields
- [x] 3.2 Update `prompts/part.md`: remove `{{PRINT_ORIENTATION}}` template slot and the "Print orientation" spec line; add coordinate vocabulary table matching planning.md

## 4. Test Fixtures

- [x] 4.1 Remove `print_orientation` from all part fixtures in `tests/test_plan_validate.py`
- [x] 4.2 Remove `print_orientation` from all part fixtures in `tests/test_orchestrate.py`
- [x] 4.3 Verify all existing tests still pass after fixture updates (`python -m pytest tests/`)

## 5. OpenSpec Spec Update

- [x] 5.1 Archive or supersede the `planning-phase` spec in `openspec/changes/cad-skill-v2/specs/planning-phase/spec.md` by noting this change supersedes it (add a comment header to that file)
