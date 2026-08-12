## Purpose

Ensures the quality gate flags a missing or empty `parameters.py` provenance file when
Phase 1 sourcing occurred but was never recorded, without blocking delivery.

## Requirements

### Requirement: Missing parameters.py detected at the gate

The quality gate SHALL emit a `warning` finding (`source: "parameters"`, `type:
"parameters_missing"`) when `build/journal.md` contains a line starting with
`- phase1/dimensions_approved` (Phase 1's dimension checkpoint recorded that sourcing
occurred) but `parameters.py` is missing or empty at the project root. The finding
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
  `phase1/dimensions_approved` line (the design had no real-world dimension lookups)
- **THEN** no `parameters_missing` finding is emitted, regardless of whether
  `parameters.py` exists

#### Scenario: Provenance file present and non-empty
- **WHEN** `build/journal.md` contains a `phase1/dimensions_approved` line and
  `parameters.py` exists at the project root with non-empty content
- **THEN** no `parameters_missing` finding is emitted

### Requirement: Project root resolution

The gate SHALL resolve both `build/journal.md` and `parameters.py` relative to the
project root, derived as the directory containing the `BUILD_PLAN.json` passed to the
gate (`plan_path`'s directory) -- the same convention `skill/phase2_planning.md`
documents for where `parameters.py` lives alongside the plan.

#### Scenario: Root derived from the plan path
- **WHEN** the gate is run with `--plan /work/proj/BUILD_PLAN.json`
- **THEN** it checks for `/work/proj/build/journal.md` and `/work/proj/parameters.py`
