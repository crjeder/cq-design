## ADDED Requirements

### Requirement: Build plan carries an optimization-mode preference

The build plan SHALL allow the user's print-optimization priority to be recorded as an
`optimize_for` preference, one of `strength`, `min_support`, or `visual_quality`, at the
plan level, with an optional per-part override of the same field. Plan validation SHALL
accept the field when present and SHALL accept plans and parts that omit it. The effective
mode for a part SHALL be its own `optimize_for` when present, otherwise the plan-level
value, otherwise `strength`. The planning phase SHALL record the mode from the user's stated
priority, and the effective mode SHALL be available to the print-orientation optimizer.

#### Scenario: Plan-level optimization mode validates

- **WHEN** a build plan declares `optimize_for: "visual_quality"` at the plan level
- **THEN** plan validation accepts it and the value is available to the orientation optimizer
  for every part lacking its own override

#### Scenario: Per-part override wins over the plan default

- **WHEN** a plan declares a plan-level `optimize_for` and one part declares a different
  `optimize_for`
- **THEN** that part's effective mode is its own value and the other parts use the plan-level
  value

#### Scenario: Plan without an optimization mode defaults to strength

- **WHEN** a plan omits `optimize_for` entirely
- **THEN** plan validation accepts it and every part's effective mode is `strength`

### Requirement: Build plan carries an optional per-part cosmetic surface

The build plan SHALL allow a part to optionally declare a `show_face` hint: the outward
normal of the part's primary cosmetic surface in its own authored frame, used by the
`visual_quality` optimization mode as the surface to orient face-down. Plan validation SHALL
accept the field when present and SHALL accept parts that omit it. When a part omits
`show_face`, the orientation optimizer infers a cosmetic surface from geometry.

#### Scenario: Plan with a declared cosmetic surface validates

- **WHEN** a part declares a `show_face` direction
- **THEN** plan validation accepts it and the value is available to the orientation optimizer

#### Scenario: Plan without a cosmetic surface is still valid

- **WHEN** a part omits the `show_face` hint
- **THEN** plan validation accepts the part and the optimizer infers a cosmetic surface when
  the visual-quality mode is active
