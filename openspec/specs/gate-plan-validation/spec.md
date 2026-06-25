# gate-plan-validation Specification

## Purpose

Define how the quality gate validates `BUILD_PLAN.json` with the shared plan validator
before running any stage that raw-indexes plan fields, so that a malformed or partial plan
fails the gate cleanly as a structured `plan_invalid` error instead of crashing the
kinematic stage with a bare traceback. The constraint-reading stages (wrapper DFM,
geometry/overhang), which read the plan only through defaulted lookups, are unaffected.

## Requirements

### Requirement: The gate validates the plan before plan-consuming stages

The quality gate SHALL validate `BUILD_PLAN.json` with the shared plan validator
(`plan_validate.validate_plan`) before running any stage that reads plan fields beyond the
defaulted constraint lookups. Validation SHALL run once, outside the fix loop. The stages
that read the plan only through defaulted `.get` lookups (wrapper DFM, geometry/overhang)
SHALL be unaffected.

#### Scenario: Validation runs once before the kinematic stage
- **WHEN** the gate runs on a plan that declares kinematics
- **THEN** the plan is validated before the kinematic stage runs, and the validation runs
  once rather than per fix-loop round

#### Scenario: Constraint-reading stages still run on a malformed plan
- **WHEN** a plan is malformed only in a field the wrapper and geometry stages never read
- **THEN** the wrapper DFM and geometry/overhang stages still run as usual

### Requirement: Plan validation failures are reported as structured issues

When the plan validator returns one or more errors, the gate SHALL emit one issue per error
matching the quality gate issue contract: `source: "plan"`, `severity: "error"`,
`type: "plan_invalid"`, a `message` carrying the validator's text, and a `hint`. These
issues SHALL block a clean pass and SHALL surface in the fix prompt.

#### Scenario: Invalid axis direction yields a structured error
- **WHEN** a kinematics entry has an `axis_dir` outside the `X`/`Y`/`Z` enum
- **THEN** the gate emits a `plate`-free `plan_invalid` error (not a raw traceback) and the
  report's `passed` is false

#### Scenario: Issue shape
- **WHEN** a `plan_invalid` issue is emitted
- **THEN** it contains `source`, `severity`, `type`, `message`, and `hint` keys and is
  consumable by the fix-prompt renderer without modification

#### Scenario: One issue per validation error
- **WHEN** the validator returns three error strings
- **THEN** the gate emits three `plan_invalid` issues, one per string

### Requirement: Plan-consuming stages are skipped when the plan is invalid

When plan validation produces any error, the gate SHALL NOT run the kinematic stage or any
other stage that raw-indexes plan fields, so a malformed plan never reaches a code path that
raises an unstructured exception. The gate SHALL still return a normal report with
`passed: false` and the `plan_invalid` errors in its issues.

#### Scenario: Malformed kinematics never reaches the sweep
- **WHEN** a plan with a malformed kinematics entry (e.g. a missing `required_range`) is
  gated
- **THEN** the kinematic stage does not run, no traceback is raised, and the report
  contains a `plan_invalid` error with `passed: false`

#### Scenario: Valid plan runs every stage unchanged
- **WHEN** a plan passes validation
- **THEN** plan validation contributes no issues, the kinematic stage runs as before, and
  the gate report (issues and print recipe) is identical to the pre-validation behavior
