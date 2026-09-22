## MODIFIED Requirements

### Requirement: Score each candidate on strength and support

For each candidate orientation the system SHALL compute a **strength score** and a
**support score**. The strength score SHALL measure how well the part's load direction
stays in the layer plane (perpendicular to build Z): higher when the load is in-plane,
lower when the load runs across layers (along build Z). The load direction SHALL be the
part's declared `load` direction. When no `load` is declared the system SHALL NOT infer a
load axis from geometry; instead the strength score SHALL be orientation-neutral (the same
value for every candidate) so that support and bed contact decide the orientation, and the
result SHALL report that no load was declared. The support score SHALL be a severity-weighted
cost of the downward-facing mesh area whose overhang angle exceeds the plan's
`overhang_max_deg` at that orientation, where each flagged face contributes by its area scaled
by how far it leans past the limit raised to an exponent (steeper overhangs cost
disproportionately more); less cost is better. The support score SHALL be slicer-free (a mesh
proxy, not a slice). Bed contact SHALL be detected within a first-layer-height band of the
lowest point so a near-coplanar resting face counts as contact.

The system SHALL additionally accept `--fem-stress <json>`, a result produced by
`src/fem_check.py` for the same part. When supplied with an `ok` result, the strength score
for each candidate SHALL be `1 - fi_p99` for that candidate from the result's
failure-index table, replacing the load-direction measure -- a solved, geometry-aware
strength in place of a direction cosine. The flag SHALL be optional: without it, or with a
`skipped` result, the strength score SHALL be exactly the load-direction measure described
above, including the orientation-neutral undeclared-load case. Candidate enumeration,
support scoring, bed-contact detection, stability, and selection SHALL be unaffected by the
flag, and the result SHALL report which strength source was used.

#### Scenario: Load across layers scores weaker than load in plane
- **WHEN** two candidate orientations are scored for a part with a declared load direction,
  one placing the load in the layer plane and one placing it along build Z
- **THEN** the in-plane orientation receives the higher strength score

#### Scenario: Steeper overhang costs more than a shallow one of equal area
- **WHEN** two candidate orientations expose equal downward overhang area above
  `overhang_max_deg`, one near-horizontal and one just past the limit
- **THEN** the near-horizontal orientation receives the worse (higher) support score

#### Scenario: Undeclared load is strength-neutral, not guessed
- **WHEN** a part has no declared `load`
- **THEN** the strength score is orientation-neutral (identical for every candidate, so
  support and bed contact decide the orientation), no load axis is inferred from geometry,
  and the result reports that no load was declared

#### Scenario: Near-coplanar resting face counts as bed contact
- **WHEN** a resting face sits within the first-layer-height band of the lowest point but
  is not exactly coplanar with the floor
- **THEN** its area is counted as bed contact

#### Scenario: FEM result replaces the direction cosine
- **WHEN** `--fem-stress` is supplied with an `ok` result for the part
- **THEN** each candidate's strength score is `1 - fi_p99` from that result's table, the
  result reports the FEM source, and support/stability/selection behave as before

#### Scenario: Two orientations with the same load direction score differently
- **WHEN** `--fem-stress` is supplied and two candidates place the declared load direction
  equally in the layer plane, but one puts the part's peak stress across layers
- **THEN** the two receive different strength scores, which the load-direction measure alone
  could not distinguish

#### Scenario: Flag absent or result skipped
- **WHEN** `--fem-stress` is not supplied, or the supplied result has `status: "skipped"`
- **THEN** the strength score is the load-direction measure, identical to the behaviour
  without this capability, and the result reports the declared-load source
