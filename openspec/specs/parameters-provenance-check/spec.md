## Purpose

Ensures the quality gate flags a missing or empty `parameters.py` provenance file when
Phase 1 sourcing occurred but was never recorded, without blocking delivery.

## Requirements

### Requirement: Missing parameters.py detected at the gate

The quality gate SHALL emit a `warning` finding (`source: "parameters"`, `type:
"parameters_missing"`) when `build/journal.md` contains a line starting with
`- phase1/dimensions_approved: parameters.py written` (Phase 1's dimension checkpoint
recorded that sourcing occurred) but `parameters.py` is missing or empty at the project root. The finding
SHALL NOT be an `error`: a missing provenance file never blocks delivery, since the
geometry it would document is unaffected.

#### Scenario: Journal records sourcing but the file is absent
- **WHEN** the gate runs, `build/journal.md` contains a `phase1/dimensions_approved`
  line, and no `parameters.py` exists at the project root
- **THEN** the report's `issues` include one `parameters_missing` finding with severity
  `warning`, and `passed` is unchanged by it

#### Scenario: Journal records sourcing but the file is empty
- **WHEN** `parameters.py` exists at the project root but is zero-length
- **THEN** one `parameters_missing` warning is emitted

#### Scenario: No journal, or journal never recorded sourcing
- **WHEN** `build/journal.md` is absent, or present but contains no
  `phase1/dimensions_approved: parameters.py written` line (the design had no
  real-world dimension lookups, e.g. `dimensions_approved: nothing sourced, ...`)
- **THEN** no `parameters_missing` finding is emitted, regardless of whether
  `parameters.py` exists

#### Scenario: Provenance file present and non-empty
- **WHEN** `build/journal.md` contains a `phase1/dimensions_approved` line and
  `parameters.py` exists at the project root with non-empty content
- **THEN** no `parameters_missing` finding is emitted

### Requirement: An unresolved dimension placeholder in parameters.py is flagged at the gate

The quality gate SHALL emit a `warning` finding (`source: "parameters"`, `type:
"parameters_unresolved"`) when `parameters.py` at the project root assigns a value of
`-1` to any name. `parameters.py` records the Phase 1 dimension table verbatim, so a
`-1` there means a `missing` row was approved despite the Phase 1 exit gate forbidding
it (see the `dimension-validation-checkpoint` and `approved-intent` specs). This is the
one place the placeholder can survive: the plan schema's size-valued fields already
reject `-1` structurally.

The finding SHALL be a `warning`, not an `error`: the geometry was built from some
concrete value regardless, so an unresolved provenance record does not block delivery.

#### Scenario: A placeholder survives into the provenance file
- **WHEN** the gate runs and `parameters.py` contains `BOWL_DIAMETER_MM = -1`
- **THEN** the report's `issues` include one `parameters_unresolved` warning naming that
  assignment, and `passed` is unchanged by it

#### Scenario: All dimensions resolved
- **WHEN** `parameters.py` exists and assigns no `-1` value
- **THEN** no `parameters_unresolved` finding is emitted

#### Scenario: A legitimate negative measurement
- **WHEN** `parameters.py` assigns a negative value other than `-1` (for example an
  offset of `-2.5`)
- **THEN** no `parameters_unresolved` finding is emitted

### Requirement: Project root resolution

The gate SHALL resolve both `build/journal.md` and `parameters.py` relative to the
project root, derived as the directory containing the `BUILD_PLAN.json` passed to the
gate (`plan_path`'s directory) -- the same convention `skill/phase2_planning.md`
documents for where `parameters.py` lives alongside the plan.

#### Scenario: Root derived from the plan path
- **WHEN** the gate is run with `--plan /work/proj/BUILD_PLAN.json`
- **THEN** it checks for `/work/proj/build/journal.md` and `/work/proj/parameters.py`
