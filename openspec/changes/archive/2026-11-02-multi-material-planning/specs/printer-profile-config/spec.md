## ADDED Requirements

### Requirement: Configured material slots
The printer profile SHALL accept an optional integer `max_materials` (>= 1), the number of
filament slots available. When absent it SHALL mean 1.

#### Scenario: Default
- **WHEN** a profile omits `max_materials`
- **THEN** the planner treats the printer as single-material

#### Scenario: Invalid value
- **WHEN** `max_materials` is 0
- **THEN** profile validation fails
