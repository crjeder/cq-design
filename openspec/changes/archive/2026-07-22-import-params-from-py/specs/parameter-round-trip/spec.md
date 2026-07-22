## ADDED Requirements

### Requirement: Parse a part script's PARAMETERS block without executing it

The tool SHALL extract every module-level assignment of a numeric literal (int, float,
or a tuple/list of numerics) from a part `.py` script using static AST analysis, without
importing CadQuery, executing the script body, or evaluating any expression other than a
literal. Assignments whose right-hand side is not a numeric literal (computed expressions,
function calls) SHALL be ignored rather than executed.

#### Scenario: Numeric literals are extracted

- **WHEN** the tool is run on a script whose PARAMETERS block contains `width = 385.0`, `depth = 120`, and `wall = 2.4`
- **THEN** it records `width=385.0`, `depth=120`, `wall=2.4` as parsed parameters

#### Scenario: Computed and non-literal assignments are skipped, not run

- **WHEN** a script assigns `inner = width - 2 * wall` or `port = port_cutout(...)` at module level
- **THEN** those names are omitted from the parsed parameters and the tool does not import CadQuery or execute the assignment

#### Scenario: A syntactically invalid script is reported, not crashed

- **WHEN** the target `.py` file cannot be parsed as Python
- **THEN** the tool emits a structured error identifying the file and exits non-zero without writing the plan

### Requirement: Reconcile conventional dimension names into the plan

The tool SHALL map the conventional part-dimension parameter names produced by the part
template -- `width` -> `dimensions.w_mm`, `depth` -> `dimensions.d_mm`, `height` ->
`dimensions.h_mm` -- for the plan part identified by `--part`, and compute the difference
between each parsed value and the current plan value.

#### Scenario: A changed dimension is diffed against the plan

- **WHEN** the script sets `width = 390` but the named part's `dimensions.w_mm` is `385`
- **THEN** the report lists `w_mm` as changed from `385` to `390`

#### Scenario: An unchanged dimension is reported as matching

- **WHEN** a parsed dimension already equals the plan value
- **THEN** the report lists it as unchanged and it is not counted as a pending write

#### Scenario: The named part must exist

- **WHEN** `--part` names an id absent from the plan's `parts`
- **THEN** the tool emits a structured error naming the missing id and exits non-zero without writing

### Requirement: Report unmapped parameters as advisory

Parsed parameters that do not correspond to a known plan field (anything other than the
conventional dimension names) SHALL be reported as advisory entries and SHALL NOT be
written into the plan.

#### Scenario: A wall or feature parameter is surfaced but not written

- **WHEN** the script sets `wall = 3.0` and `boss_dia = 6`, neither of which maps to a plan field
- **THEN** the report lists both under advisory/unmapped and the plan's contents for those concepts are left unchanged

### Requirement: Guard the write-back with schema validation

By default the tool SHALL perform a dry run, emitting the diff report without modifying
any file. When `--write` is given, the tool SHALL apply the mapped changes to an
in-memory copy of the plan, re-validate that copy against the BUILD_PLAN JSON Schema, and
persist it only if validation passes; on validation failure it SHALL emit the validation
errors and leave `BUILD_PLAN.json` unchanged.

#### Scenario: Dry run leaves files untouched

- **WHEN** the tool is run without `--write`
- **THEN** it prints the diff report and `BUILD_PLAN.json` on disk is byte-for-byte unchanged

#### Scenario: A valid update is written

- **WHEN** the tool is run with `--write` and the resulting plan passes schema validation
- **THEN** `BUILD_PLAN.json` is updated with the new dimension values and the report confirms the write

#### Scenario: An update that would break the schema is refused

- **WHEN** applying a parsed value would produce a plan that fails schema validation (e.g. a non-positive dimension)
- **THEN** the tool reports the validation errors, does not modify `BUILD_PLAN.json`, and exits non-zero

### Requirement: Emit a structured JSON report

The tool SHALL emit a JSON object describing the run with at least `part`, `changed`
(list of `{field, from, to}`), `unchanged` (list of fields), `unmapped` (list of parsed
parameter names), `written` (boolean), and `errors` (list, empty on success).

#### Scenario: Report shape is stable

- **WHEN** any run completes
- **THEN** the emitted JSON contains the keys `part`, `changed`, `unchanged`, `unmapped`, `written`, and `errors`
