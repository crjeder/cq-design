## ADDED Requirements

### Requirement: Optional bridge length limit
`printer_profile.json` SHALL accept an optional `constraints.bridge_max_mm` (number, minimum 0). When absent, consumers SHALL use 10.0.

#### Scenario: Existing profile still validates
- **WHEN** a profile without `bridge_max_mm` is validated
- **THEN** validation succeeds

#### Scenario: Negative value rejected
- **WHEN** `bridge_max_mm` is -1
- **THEN** validation fails
