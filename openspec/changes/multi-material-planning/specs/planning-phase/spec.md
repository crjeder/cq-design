## ADDED Requirements

### Requirement: Multi-material proposals
The planner SHALL default to a single material and SHALL add a second material only when the
user asks or when it states a concrete trigger (compliant part against rigid, soluble
support, heat zone) in the plan rationale. The planner SHALL NOT rely on adhesion between
different materials for load transfer.

#### Scenario: User requests
- **WHEN** the user asks for a TPU grip on a PLA body
- **THEN** the plan assigns TPU to the grip union and PLA to the body

#### Scenario: Planner suggests
- **WHEN** a part needs a gasket against a rigid housing
- **THEN** the planner proposes TPU for the gasket union and names the trigger

#### Scenario: Slots exceeded
- **WHEN** the plan needs more materials than `max_materials`
- **THEN** the planner shows the warning and asks the user before approval
