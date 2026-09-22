## ADDED Requirements

### Requirement: Optional motion block for toolhead speed modeling

`printer_profile.json` SHALL accept an optional top-level `motion` object carrying
`v_cruise_mm_s`, `accel_mm_s2`, `junction_deviation_mm`, `min_layer_time_s`,
`layer_height_mm`, `line_width_mm`, and `infill_density` (all positive numbers). The
file's shape SHALL be validated against the updated `src/printer_profile_schema.json`.
When `motion` is absent, consumers that need it (the toolpath-speed-advisor capability)
SHALL treat this as a stated skip and SHALL NOT assume default values for any of its
fields. Existing profiles without a `motion` block SHALL continue to validate.

#### Scenario: Profile with a valid motion block validates

- **WHEN** `printer_profile.json` declares a `motion` object with all seven fields as
  positive numbers
- **THEN** validation passes and the values are available to consumers that use them

#### Scenario: Profile without a motion block still validates

- **WHEN** `printer_profile.json` omits `motion` entirely
- **THEN** validation passes, exactly as before this capability existed

#### Scenario: Partial motion block is rejected, not defaulted

- **WHEN** `printer_profile.json` declares a `motion` object missing one of the seven
  required fields
- **THEN** validation fails, naming the missing field, rather than silently defaulting it

#### Scenario: Per-model override persists into the motion block

- **WHEN** the user explicitly states a different `motion.accel_mm_s2` for the current
  model without indicating a one-time exception
- **THEN** `printer_profile.json` is rewritten with the new value under `motion`, other
  `motion` fields and top-level fields are unchanged, and the file re-validates
