## ADDED Requirements

### Requirement: Prose does not restate a code-enforced contract
A `SKILL.md` or `skill/phase*.md` file SHALL NOT restate the substantive
content of a fact that a JSON Schema, a validator/runner script's typed
output (e.g. error names, hint text, contract keys), an AST lint check, or a
machine-readable inventory file (e.g. `blocks/inventory.json`) already
defines or enforces at run time. Such prose SHALL instead name the enforcing
file and, at most, a short category summary, rather than duplicating the
enumerated values, exact wording, or full field list. This is distinct from
the existing requirement against restating a guaranteed-in-context document
read: this requirement applies even when the enforcing file is not read into
context during the phase, because the enforcing file -- not the doc -- is
the source of truth and the one that changes first when behavior changes.

#### Scenario: Typed error table restated in prose
- **WHEN** a phase file or SKILL.md lists typed error names together with
  their exact remediation hint text
- **THEN** the list is replaced with a short category summary plus a pointer
  to the script (e.g. `run_cadquery_model.py`'s `errors[].hint`,
  `cq_verify.py`) that generates the names and hints, so a new or renamed
  error type does not require a matching doc edit to stay accurate

#### Scenario: Lint-check list restated in prose
- **WHEN** a phase file spells out the AST lint checks a lint script
  implements (e.g. by describing each check in prose)
- **THEN** the phase file instead points to the single authoritative list of
  check names (in `reference/scripts.md`, itself describing
  `script_lint.py`) rather than carrying its own restatement

#### Scenario: Inventory data restated in prose
- **WHEN** a phase file tabulates block names, uses, or parameters that a
  machine-readable inventory file (`blocks/inventory.json`) already carries
- **THEN** the table is removed and only the procedural instruction to
  consult the inventory file remains, unless the phase file's row carries
  procedural guidance absent from the inventory file itself

#### Scenario: A schema-owned field is described only by name
- **WHEN** a phase file or SKILL.md needs to mention a JSON contract field
  whose shape (subfields, enum values, aggregation behavior) is defined by
  a runner script or JSON Schema
- **THEN** the doc names the field and the file that defines its shape,
  and does not reproduce the field's internal structure
