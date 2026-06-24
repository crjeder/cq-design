## MODIFIED Requirements

### Requirement: Enumerate stable candidate print orientations

The system SHALL enumerate candidate bed-down print orientations for a union mesh as the
set of orientations that lay a flat face on the bed: the convex hull's significant resting
facets, the six axis-aligned bounding-box faces as a baseline, and an area-cumulation
source that accumulates face normals weighted by face area and contributes the top-N
directions by accumulated area. Each candidate SHALL be the rotation that maps the chosen
face's outward normal to -Z. Candidates whose bed-down normals coincide within an angular
tolerance SHALL be deduplicated so the candidate set is bounded.

#### Scenario: Axis-aligned baseline is always present
- **WHEN** a union mesh is enumerated for candidate orientations
- **THEN** the six axis-aligned bed-down orientations are included even if no convex-hull
  facet is significant

#### Scenario: Near-duplicate resting faces are merged
- **WHEN** two candidate bed-down normals differ by less than the angular tolerance
- **THEN** only one orientation is kept for that direction

#### Scenario: Large flat area surfaces as a candidate
- **WHEN** a mesh has a large flat region whose accumulated area dominates other directions
- **THEN** the orientation laying that region on the bed is present among the candidates
  via the area-cumulation source

### Requirement: Score each candidate on strength and support

For each candidate orientation the system SHALL compute a **strength score** and a
**support score**. The strength score SHALL measure how well the part's load direction
stays in the layer plane (perpendicular to build Z): higher when the load is in-plane,
lower when the load runs across layers (along build Z). The load direction SHALL be the
part's declared `load` when present and an inferred principal axis otherwise. The support
score SHALL be a severity-weighted cost of the downward-facing mesh area whose overhang
angle exceeds the plan's `overhang_max_deg` at that orientation, where each flagged face
contributes by its area scaled by how far it leans past the limit raised to an exponent
(steeper overhangs cost disproportionately more); less cost is better. The support score
SHALL be slicer-free (a mesh proxy, not a slice). Bed contact SHALL be detected within a
first-layer-height band of the lowest point so a near-coplanar resting face counts as
contact.

#### Scenario: Load across layers scores weaker than load in plane
- **WHEN** two candidate orientations are scored for a part with a declared load direction,
  one placing the load in the layer plane and one placing it along build Z
- **THEN** the in-plane orientation receives the higher strength score

#### Scenario: Steeper overhang costs more than a shallow one of equal area
- **WHEN** two candidate orientations expose equal downward overhang area above
  `overhang_max_deg`, one near-horizontal and one just past the limit
- **THEN** the near-horizontal orientation receives the worse (higher) support score

#### Scenario: Load direction is inferred when undeclared
- **WHEN** a part has no declared `load`
- **THEN** the strength score is computed against a geometry-inferred principal load axis
  and the inferred direction is reported in the result

#### Scenario: Near-coplanar resting face counts as bed contact
- **WHEN** a resting face sits within the first-layer-height band of the lowest point but
  is not exactly coplanar with the floor
- **THEN** its area is counted as bed contact

## ADDED Requirements

### Requirement: Build-height optimization objective

The system SHALL provide a `min_build_height` optimization objective that selects the
candidate orientation minimizing the posed bounding-box extent along build Z, within a
tolerance band, breaking ties by the strength and support scores and a deterministic
index. Selecting this objective SHALL NOT change the scores computed for each candidate,
only which candidate is chosen.

#### Scenario: Lowest profile is selected
- **WHEN** orientation optimization runs with `optimize_for` set to `min_build_height`
- **THEN** the candidate with the smallest posed Z extent is selected, ties broken by
  strength then support

#### Scenario: Build-height mode is deterministic
- **WHEN** the `min_build_height` objective is run twice on the same mesh and constraints
- **THEN** it returns the same recommended orientation and scores
