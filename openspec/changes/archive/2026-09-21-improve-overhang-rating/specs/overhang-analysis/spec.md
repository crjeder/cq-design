## ADDED Requirements

### Requirement: Short bridges are not overhangs
The analysis SHALL group unsupported down-facing faces into connected regions and SHALL classify a near-horizontal region (mean overhang angle >= 80 degrees) whose shortest in-plane extent is at most `constraints.bridge_max_mm` (default 10.0) and that is supported on at least two sides (boundary edges shared with wall or up-facing faces covering at least two distinct sides of the region's oriented rectangle) as a bridge. Bridge area SHALL be reported as `bridge_area_mm2` and SHALL NOT be included in `overhang_area_mm2` or trigger `overhang_exceeded`.

#### Scenario: Short bridge not flagged
- **WHEN** a part has a horizontal ceiling spanning 6 mm between two walls and `bridge_max_mm` is 10
- **THEN** no `overhang_exceeded` issue is emitted and `bridge_area_mm2` is greater than 0

#### Scenario: Long span still flagged
- **WHEN** the same ceiling spans 25 mm
- **THEN** the region counts toward `overhang_area_mm2` and `overhang_exceeded` is emitted

#### Scenario: Short cantilever is not a bridge
- **WHEN** a horizontal ledge 6 mm wide projects from a single wall and is free on its other sides
- **THEN** it counts toward `overhang_area_mm2` and `overhang_exceeded` is emitted

#### Scenario: Ceiling supported on two sides is a bridge
- **WHEN** a horizontal ceiling 6 mm wide is joined to walls on two opposite sides
- **THEN** it is classified as a bridge

#### Scenario: Steep non-horizontal overhang is never a bridge
- **WHEN** a 60 degree overhang region has a shortest extent of 3 mm
- **THEN** it counts as an overhang, not a bridge

### Requirement: Overhang area is independent of tessellation
`overhang_area_mm2` SHALL be unchanged (within 1%) when the same surface is re-meshed with a different triangle density.

#### Scenario: Refined mesh gives same area
- **WHEN** a curved overhang surface is subdivided to 4x the triangle count
- **THEN** `overhang_area_mm2` differs by less than 1%
