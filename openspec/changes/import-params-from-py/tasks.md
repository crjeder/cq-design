## 1. Parameter parsing

- [ ] 1.1 Add `src/import_params.py` with `parse_parameters(script_path) -> dict[str, int|float|tuple]`: `ast.parse` the file, walk module-level `ast.Assign` nodes with a single `ast.Name` target, keep values where `ast.literal_eval` yields an int/float (or tuple/list of those); skip everything else.
- [ ] 1.2 Raise/return a structured error (not a traceback) when the file is missing or not parseable as Python.

## 2. Plan reconciliation

- [ ] 2.1 Add the fixed name map `{"width": "w_mm", "depth": "d_mm", "height": "h_mm"}` and a `reconcile(parsed, plan, part_id)` that locates the part, computes `changed`/`unchanged` for mapped dimensions, and collects `unmapped` for the rest.
- [ ] 2.2 Return a structured error when `part_id` is not present in `plan["parts"]`.

## 3. Write-back guard

- [ ] 3.1 Import the schema-validation entry point from `plan_validate.py`; apply changes to a deep copy and validate before persisting.
- [ ] 3.2 On `--write` + valid: persist with `json.dump(..., indent=2, ensure_ascii=False)`. On invalid: emit validation errors, leave the file untouched, exit non-zero.
- [ ] 3.3 Default (no `--write`): dry run -- emit the report, touch nothing.

## 4. CLI and JSON contract

- [ ] 4.1 `argparse` CLI: positional `script`, `--part` (required), `--plan` (default `BUILD_PLAN.json`), `--write`.
- [ ] 4.2 Emit the report JSON with keys `part`, `changed` (`{field, from, to}`), `unchanged`, `unmapped`, `written`, `errors`; set exit code (0 clean, non-zero on error/refused write).

## 5. Tests

- [ ] 5.1 Add `tests/test_import_params.py` (no CadQuery, fast tier like `test_plan_validate.py`): parsing literals vs. skipping computed/call assignments.
- [ ] 5.2 Reconciliation: changed dim diffed, unchanged excluded, unmapped surfaced, missing part errors.
- [ ] 5.3 Write guard: dry run leaves file byte-identical; valid `--write` updates dimensions; a value that breaks the schema is refused and the file is unchanged.
- [ ] 5.4 Invalid/unparseable script and missing plan file each produce a structured error and non-zero exit.

## 6. Documentation

- [ ] 6.1 Add `src/import_params.py` to the Core Scripts table and File Layout in `CLAUDE.md`.
- [ ] 6.2 Add a workflow note in `SKILL.md` telling users to run the round-trip after hand-editing a part script's `PARAMETERS` block instead of editing `BUILD_PLAN.json` directly.
