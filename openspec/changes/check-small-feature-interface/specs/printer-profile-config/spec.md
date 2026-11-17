## ADDED Requirements

### Requirement: Minimum interface area constraint
The printer profile and `BUILD_PLAN.json` constraints SHALL accept an optional `interface_min_area_mm2` (number, greater than 0). The default profile SHALL set it to 4.0, and when it is absent the step-form build SHALL use 4.0. Profiles written before this field existed SHALL still validate.

#### Scenario: Default profile declares the field
- **WHEN** `src/profile.default.json` is validated against `src/printer_profile_schema.json`
- **THEN** it passes and `constraints.interface_min_area_mm2` is 4.0

#### Scenario: Older profile without the field
- **WHEN** a `profile.json` omits `interface_min_area_mm2`
- **THEN** validation passes and the neck check uses 4.0

#### Scenario: Non-positive value
- **WHEN** `interface_min_area_mm2` is 0 or negative
- **THEN** validation fails naming the field
