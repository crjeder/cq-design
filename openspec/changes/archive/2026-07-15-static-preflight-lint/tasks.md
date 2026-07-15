## 1. Linter core

- [x] 1.1 Create `src/script_lint.py` with the AST visitor skeleton, finding
  dataclass (`type`, `message`, `hint`, `line`), and `lint_script(path) -> list`
  entry (stdlib only; `syntax_error` finding on parse failure)
- [x] 1.2 Implement structural checks: `boolean_in_loop`, `missing_result`,
  `submodule_import`, `direct_export`, `shell_after_fillet`
- [x] 1.3 Implement heuristic checks with the narrow scoping from design.md:
  `magic_number` (PARAMETERS-block exemption + literal exempt-list),
  `unanchored_feature`, `unguarded_boolean`
- [x] 1.4 Add CLI: `python src/script_lint.py <script.py>` printing
  `{"success": bool, "findings": [...]}`, exit 0 clean / 1 findings

## 2. Tests

- [x] 2.1 Create `tests/test_script_lint.py` (no CadQuery): one positive and one
  negative case per finding type, using inline script fixtures
- [x] 2.2 Cover the contract: finding field shape, clean-script empty output,
  syntax-error handling, CLI exit codes
- [x] 2.3 Run a corpus sanity pass: lint the eval-case golden plans' style of
  scripts and any `tests/fixtures` part scripts; confirm no false positives

## 3. Integration

- [x] 3.1 Add SKILL.md part-loop "Step 2.5 - lint before validate": run the linter,
  fix findings, re-lint before the first `run_cadquery_model.py` call
- [x] 3.2 Add `script_lint.py` to the Core Scripts table in CLAUDE.md and the file
  layout listing
- [x] 3.3 `ruff check --fix` + `ruff format` on new files; full fast test subset
  (`uv run pytest tests/test_script_lint.py tests/test_plan_validate.py`)
