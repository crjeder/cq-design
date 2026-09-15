## ADDED Requirements

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
