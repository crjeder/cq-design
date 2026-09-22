## MODIFIED Requirements

### Requirement: The gate validates the plan before plan-consuming stages

The quality gate SHALL validate `BUILD_PLAN.json` with the shared plan validator
(`plan.validate_plan`) before running any stage that reads plan fields beyond the
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
