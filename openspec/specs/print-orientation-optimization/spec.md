# print-orientation-optimization Specification

## Purpose

Define how a recommended print orientation is chosen for each union: enumerate stable
bed-down candidate orientations, score each on layer-plane strength and slicer-free
support, select strength-first and support-second, and emit the chosen orientation as a
rotation transform with rationale that the design phase can act on.

## Requirements

### Requirement: Enumerate stable candidate print orientations

The system SHALL enumerate candidate bed-down print orientations for a union mesh as the
set of orientations that lay a flat face on the bed: the convex hull's significant resting
facets plus the six axis-aligned bounding-box faces as a baseline. Each candidate SHALL be
the rotation that maps the chosen face's outward normal to -Z. Candidates whose bed-down
normals coincide within an angular tolerance SHALL be deduplicated so the candidate set is
bounded.

#### Scenario: Axis-aligned baseline is always present
- **WHEN** a union mesh is enumerated for candidate orientations
- **THEN** the six axis-aligned bed-down orientations are included even if no convex-hull
  facet is significant

#### Scenario: Near-duplicate resting faces are merged
- **WHEN** two candidate bed-down normals differ by less than the angular tolerance
- **THEN** only one orientation is kept for that direction

### Requirement: Score each candidate on strength and support

For each candidate orientation the system SHALL compute a **strength score** and a
**support score**. The strength score SHALL measure how well the part's load direction
stays in the layer plane (perpendicular to build Z): higher when the load is in-plane,
lower when the load runs across layers (along build Z). The load direction SHALL be the
part's declared `load` when present and an inferred principal axis otherwise. The support
score SHALL be derived from the downward-facing mesh area whose overhang angle exceeds the
plan's `overhang_max_deg` at that orientation (less overhang area is better), and SHALL be
slicer-free (a mesh proxy, not a slice).

#### Scenario: Load across layers scores weaker than load in plane
- **WHEN** two candidate orientations are scored for a part with a declared load direction,
  one placing the load in the layer plane and one placing it along build Z
- **THEN** the in-plane orientation receives the higher strength score

#### Scenario: Support score reflects overhang area at the candidate pose
- **WHEN** a candidate orientation exposes more downward face area above `overhang_max_deg`
  than another
- **THEN** that orientation receives the worse (higher-support) score

#### Scenario: Load direction is inferred when undeclared
- **WHEN** a part has no declared `load`
- **THEN** the strength score is computed against a geometry-inferred principal load axis
  and the inferred direction is reported in the result

### Requirement: Select orientation strength-first, support-second

The system SHALL select the recommended orientation lexicographically: the candidate with
the best strength score, breaking ties within a strength tolerance band by the best
(lowest) support score. The selection SHALL NOT trade strength away to reduce support
outside the tolerance band.

#### Scenario: Strength wins over support
- **WHEN** one candidate has clearly higher strength but more support, and another has less
  support but clearly lower strength
- **THEN** the higher-strength candidate is selected

#### Scenario: Support breaks a strength tie
- **WHEN** two candidates have strength scores within the tolerance band
- **THEN** the one with the lower support score is selected

### Requirement: Emit the chosen orientation transform with rationale

The system SHALL emit, per union, the recommended print orientation as a rotation
transform (compatible with the `placement.py` rotation convention), together with the
strength and support score breakdown and a human-readable rationale. This output SHALL be
distinct from the union's assembled-frame `placement`.

#### Scenario: Result carries transform plus scores
- **WHEN** orientation optimization completes for a union
- **THEN** the result contains the rotation transform, the strength score, the support
  score, and a rationale string, and does not overwrite the union's `placement`

### Requirement: Optimization runs as a bounded loop the design phase can act on

The orientation scoring SHALL be exposed as a deterministic tool so the design loop can
re-run it after a targeted geometry change (for example chamfering a steep overhang to
reduce the support the best-strength orientation still incurs) and converge within a
bounded number of iterations. Repeated runs on identical input SHALL produce identical
recommendations.

#### Scenario: Re-scoring after a geometry tweak
- **WHEN** the geometry is edited to reduce overhang and the tool is re-run at the same
  orientation
- **THEN** the support score improves and the new recommendation reflects the edited mesh

#### Scenario: Deterministic output
- **WHEN** the tool is run twice on the same mesh, load, and constraints
- **THEN** it returns the same recommended orientation and scores
