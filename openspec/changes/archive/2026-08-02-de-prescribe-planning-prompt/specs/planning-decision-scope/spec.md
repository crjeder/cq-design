## ADDED Requirements

### Requirement: Minor design decisions are decided and recorded, not asked

`prompts/planning.md` SHALL instruct the planner to decide minor choices itself and
record each in `planning_notes`, rather than asking the user. A choice is minor when a
different answer changes neither the topology, nor a dimension, nor a fit: a coined part
or interface name, a clearance value already given by the fit-type table for the stated
fit, plate grouping, and equivalent defaults.

This carve-out SHALL NOT weaken the existing ask rules. A dimension that could not be
verified (rule 1), an unclear fit type (rule 4), and an undeterminable load (rule 10)
remain questions for the user.

#### Scenario: Coined name is decided, not asked

- **WHEN** the user never named a part that the plan needs an id for
- **THEN** the planner coins the id, records it in `planning_notes`, and does not ask the
  user to choose a name before producing the plan

#### Scenario: Table-default clearance is decided, not asked

- **WHEN** the fit type of a mating interface is stated or unambiguous and the fit-type
  table supplies a default clearance
- **THEN** the planner uses that default and does not ask the user to confirm the value

#### Scenario: Unverifiable dimension is still asked

- **WHEN** a real-world dimension could not be verified from two sources
- **THEN** the planner writes `-1`, records the unknown in `planning_notes`, and asks the
  user for the value before finalizing the plan

#### Scenario: Unclear fit type is still asked

- **WHEN** the fit type of a mating interface cannot be determined from the request
- **THEN** the planner asks the user which fit is intended rather than picking a default

### Requirement: Decided minor choices are visible to the user before the build

Every minor choice the planner decided under the carve-out SHALL be recoverable from
`planning_notes`, and every coined name SHALL still be introduced explicitly in the
Phase 2 plan summary checkpoint so the user can correct it before Phase 3 starts.

#### Scenario: Coined name surfaces at the plan summary

- **WHEN** the plan contains a part id or interface name the user never used
- **THEN** the Phase 2 plan summary names it explicitly (e.g. "I'm calling the bottom
  part `base`") and the user can correct it before the build loop starts
