## Purpose

Static, AST-based pre-flight lint for generated CadQuery part scripts. Catches
mechanically-detectable anti-patterns before the part loop spends a full CadQuery
subprocess run, using only the Python standard library.

## Requirements

### Requirement: AST-based lint without CadQuery
The system SHALL provide `src/script_lint.py`, which analyzes a part script using
only the Python standard library (`ast`, `json`) and SHALL NOT import CadQuery or
any third-party package.

#### Scenario: Lint runs without CadQuery installed
- **WHEN** `script_lint.py` is invoked in an environment without CadQuery
- **THEN** it completes and returns findings normally

#### Scenario: Syntactically invalid script
- **WHEN** the target script fails to parse
- **THEN** the linter reports a single `syntax_error` finding with the parse error
  message and line number instead of raising

### Requirement: Anti-pattern finding catalog
The linter SHALL detect the following anti-patterns, each with a stable `type`
identifier: `boolean_in_loop`, `missing_result`, `submodule_import`,
`direct_export`, `magic_number`, `unanchored_feature`, `unguarded_boolean`,
`shell_after_fillet`.

#### Scenario: Boolean inside a loop
- **WHEN** a script calls `.cut(...)`, `.union(...)`, or `.intersect(...)` inside a
  `for` or `while` body
- **THEN** a `boolean_in_loop` finding is reported with the offending line number

#### Scenario: Missing result assignment
- **WHEN** a script contains no top-level assignment to `result`
- **THEN** a `missing_result` finding is reported

#### Scenario: Submodule block import
- **WHEN** a script imports from a `blocks` submodule (e.g.
  `from blocks.primitives import fillet_box`)
- **THEN** a `submodule_import` finding is reported with a hint to import from
  `blocks` directly

#### Scenario: Direct exporter call
- **WHEN** a script calls `cq.exporters.export(...)`
- **THEN** a `direct_export` finding is reported with a hint that the shim owns
  export

#### Scenario: Shell after fillet
- **WHEN** a fluent chain calls `.shell(...)` after `.fillet(...)`
- **THEN** a `shell_after_fillet` finding is reported

#### Scenario: Clean script produces no findings
- **WHEN** a script contains none of the cataloged anti-patterns
- **THEN** the findings list is empty and `success` is `true`

### Requirement: Shared finding contract
Each finding SHALL carry `type`, `message`, `hint`, and `line` fields, matching the
shape of the wrapper's `errors` entries so the part loop can build correction
prompts without a second parser.

#### Scenario: Finding shape
- **WHEN** any anti-pattern is detected
- **THEN** the emitted finding contains non-empty `type`, `message`, and `hint`
  strings and an integer `line`

### Requirement: CLI entry point with pass/fail exit code
The linter SHALL be invocable as `python src/script_lint.py <script.py>`, SHALL
print a JSON object `{"success": <bool>, "findings": [...]}` to stdout, and SHALL
exit 0 when no findings exist and 1 when findings exist.

#### Scenario: Clean script exit code
- **WHEN** the CLI is run against a script with no findings
- **THEN** it prints `{"success": true, "findings": []}` and exits 0

#### Scenario: Script with findings exit code
- **WHEN** the CLI is run against a script containing anti-patterns
- **THEN** it prints `success: false` with the findings array and exits 1

### Requirement: Part-loop integration before first run
The SKILL.md part loop SHALL include a step ("Step 2.5") that runs the linter on
each generated part script and requires findings to be fixed before the first
`run_cadquery_model.py` invocation.

#### Scenario: Lint gate before wrapper run
- **WHEN** a generated part script produces lint findings
- **THEN** the part loop revises the script and re-lints before spending a CadQuery
  run
