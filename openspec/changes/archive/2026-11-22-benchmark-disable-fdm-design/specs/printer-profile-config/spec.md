## ADDED Requirements

### Requirement: Optional design_intent field

`src/printer_profile_schema.json` SHALL define an optional top-level `design_intent` with
enum `["print", "cad"]`. `src/profile.default.json` SHALL NOT set it. Behavior of each value
is defined by the `design-intent-mode` capability.

#### Scenario: Profile with cad intent
- **WHEN** a profile otherwise valid sets `design_intent` to `"cad"`
- **THEN** validation passes

#### Scenario: Default profile
- **WHEN** `src/profile.default.json` is validated
- **THEN** validation passes and the file has no `design_intent` key
