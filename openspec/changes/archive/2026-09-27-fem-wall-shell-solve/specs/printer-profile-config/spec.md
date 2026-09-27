## ADDED Requirements

### Requirement: Optional top/bottom shell layer count

`printer_profile.json` SHALL accept an optional `constraints.top_bottom_layers` (integer,
minimum 1). When absent, consumers SHALL use 4, matching the value already assumed before
this capability existed.

#### Scenario: Existing profile without the field still validates
- **WHEN** a profile without `constraints.top_bottom_layers` is validated
- **THEN** validation succeeds

#### Scenario: Declared value is used by print-recipe generation
- **WHEN** a profile declares `constraints.top_bottom_layers: 6`
- **THEN** `quality_gate.py`'s generated print recipe uses `6`, not the previous hardcoded
  default of `4`

#### Scenario: Value below the minimum is rejected
- **WHEN** `constraints.top_bottom_layers` is `0`
- **THEN** validation fails, naming the field, rather than silently clamping it

### Requirement: Declared `motion.layer_height_mm` is authoritative for print-recipe generation

When `printer_profile.json` declares a `motion` block, the system SHALL use its
`layer_height_mm` as the print recipe's `layer_height_mm` instead of deriving it from
`nozzle_mm`. When no `motion` block is declared, consumers SHALL continue to derive
`layer_height_mm` as `nozzle_mm * 0.5`, exactly as before this capability existed.

#### Scenario: Motion block's layer height overrides the nozzle-derived default
- **WHEN** a profile declares `motion.layer_height_mm: 0.16` with `nozzle_mm: 0.4`
- **THEN** the generated print recipe's `layer_height_mm` is `0.16`, not `0.2`

#### Scenario: No motion block keeps the existing derivation
- **WHEN** a profile declares no `motion` block
- **THEN** the generated print recipe's `layer_height_mm` is `nozzle_mm * 0.5`, exactly as
  before this capability existed
