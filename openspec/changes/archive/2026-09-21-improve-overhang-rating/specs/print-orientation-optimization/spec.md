## ADDED Requirements

### Requirement: Support score is region-based, bridge-aware and continuous
The support score SHALL be computed per overhang region using a severity ramp that is zero at `overhang_max_deg` and rises continuously to 1 at horizontal, raised to the exponent `OV_H`. Bridge regions (see overhang-analysis) SHALL contribute at most 10% of their non-bridge cost.

#### Scenario: Bridge does not drive orientation
- **WHEN** two candidate poses differ only in that one leaves a 6 mm bridge
- **THEN** the pose without the bridge scores at most marginally better, and a pose with a real 30 mm overhang scores clearly worse than both

#### Scenario: No cliff at the limit
- **WHEN** a face's angle moves from `overhang_max_deg - 0.1` to `overhang_max_deg + 0.1`
- **THEN** the support score changes by less than 0.1% of the face area

### Requirement: Orientation ranking is deterministic
Given the same mesh and options, the optimizer SHALL return the same orientation on repeated runs, resolving ties within a band by a fixed key order independent of candidate enumeration order.

#### Scenario: Repeated runs agree
- **WHEN** the optimizer runs twice on the same STL
- **THEN** both results carry the same `rotate` steps and score
