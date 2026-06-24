## ADDED Requirements

### Requirement: Build plan carries an optional per-part load hint

The build plan SHALL allow a part to optionally declare a `load` hint: the principal load
direction in the part's own authored frame, used to drive print-orientation strength
scoring. Plan validation SHALL accept the field when present (a direction in the authored
frame) and SHALL accept parts that omit it. When a
part declares `load`, the planning summary SHALL surface it; when absent, downstream
strength scoring infers a load axis from geometry.

#### Scenario: Plan with a declared load validates
- **WHEN** a build plan declares a `load` direction on a part
- **THEN** plan validation accepts it and the value is available to the orientation
  optimizer

#### Scenario: Plan without a load hint is still valid
- **WHEN** a part omits the `load` hint
- **THEN** plan validation accepts the part and strength scoring falls back to a
  geometry-inferred load axis
