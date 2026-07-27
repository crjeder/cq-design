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

### Requirement: Select orientation by the requested optimization mode

The system SHALL select the recommended orientation according to a requested optimization
mode, one of `strength`, `min_support`, or `visual_quality` (default `strength`). For each
mode the selection SHALL be a deterministic lexicographic ordering over the scored
candidates with a tolerance band on the primary key so near-ties fall through to the next
key:

- `strength`: primary best strength (higher), ties within the strength band broken by least
  support, then most bed contact. (Unchanged from prior behavior.)
- `min_support`: primary least support (lower), ties within a support band broken by best
  strength, then most bed contact.
- `visual_quality`: primary best visual score (higher), ties within a visual band broken by
  best strength, then least support.

In every mode the final tiebreak SHALL be deterministic so the same input and mode always
yield the same pick.

#### Scenario: Strength mode prefers strength over support

- **WHEN** the mode is `strength` and one candidate has clearly higher strength but more
  support while another has less support but clearly lower strength
- **THEN** the higher-strength candidate is selected

#### Scenario: Min-support mode minimizes support

- **WHEN** the mode is `min_support` and one candidate needs clearly less support than a
  stronger candidate outside the support band
- **THEN** the lower-support candidate is selected, with strength used only to break a
  support tie

#### Scenario: Visual mode optimizes appearance first

- **WHEN** the mode is `visual_quality` and one candidate has a clearly better visual score
  than a stronger or lower-support candidate outside the visual band
- **THEN** the better-visual candidate is selected, with strength and support used only as
  tiebreakers

#### Scenario: Default mode is strength

- **WHEN** no optimization mode is requested
- **THEN** the selection behaves as `strength`

### Requirement: Emit the chosen orientation transform with rationale

The system SHALL emit, per union, the recommended print orientation as a rotation
transform (compatible with the `placement.py` rotation convention), together with the
strength, support, and visual score breakdown, the active optimization mode, and a
human-readable rationale that names the mode and explains why the pose won under it. This
output SHALL be distinct from the union's assembled-frame `placement`.

The orientation tool SHALL accept an optional source-script path identifying the part
script whose authored-frame geometry produced the mesh being scored. When supplied, the
result SHALL carry that script's provenance stamp (`source_script_hash`) so the result is
self-describing about which script version it was computed from. When omitted, the result
SHALL carry no such stamp, and a consumer comparing against it SHALL treat the absence as
unknown provenance, not a mismatch.

#### Scenario: Result carries transform, scores, and mode

- **WHEN** orientation optimization completes for a union
- **THEN** the result contains the rotation transform, the strength score, the support
  score, the visual score, the active `optimize_for` mode, and a rationale string, and does
  not overwrite the union's `placement`

#### Scenario: Source script is stamped when supplied

- **WHEN** the orientation tool is invoked with a source-script path
- **THEN** the result carries that script's provenance stamp

#### Scenario: Result is unstamped when no source script is given

- **WHEN** the orientation tool is invoked without a source-script path
- **THEN** the result carries no provenance stamp, and a consumer treats this as unknown
  provenance rather than a staleness mismatch

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

### Requirement: Score each candidate on visual quality

For each candidate orientation the system SHALL compute a **visual score** combining two
slicer-free mesh proxies: a **gentle-incline penalty** and a **cosmetic-face-down reward**.
The gentle-incline penalty SHALL be derived from the fraction of (visible, non-bed) face
area whose surface is shallowly sloped — neither near-flat nor near-vertical — specifically
faces whose normal lies within the gentle-incline zone bounded by 45 degrees, which
stair-steps visibly in FDM. The cosmetic-face-down reward SHALL measure how well the part's
cosmetic surface normal points at the bed (-Z) in that orientation, since the first layer
against the smooth bed has the best finish. A higher visual score SHALL indicate a more
visually favorable orientation (less gentle-incline area, cosmetic surface more nearly
face-down). The visual score SHALL be slicer-free (a mesh proxy, not a slice).

#### Scenario: Gentle inclines lower the visual score

- **WHEN** two candidate orientations are scored and one exposes more shallow-incline
  (under 45 degrees) visible face area than the other
- **THEN** the orientation with more gentle-incline area receives the worse (lower) visual
  score

#### Scenario: Cosmetic surface facing the bed raises the visual score

- **WHEN** two candidate orientations differ only in whether the part's cosmetic surface
  faces the bed
- **THEN** the orientation placing the cosmetic surface face-down receives the higher visual
  score

#### Scenario: Visual scoring is slicer-free and deterministic

- **WHEN** the visual score is computed twice for the same mesh, cosmetic surface, and
  orientation
- **THEN** it is computed without invoking a slicer and returns the same value

### Requirement: Cosmetic surface is declared or inferred

The system SHALL accept an optional cosmetic surface direction (a `show_face` outward normal
in the part's authored frame) used by the visual score as the surface to orient face-down.
When the cosmetic surface is not declared, the system SHALL infer one from geometry (for
example the outward normal of the largest planar face) and SHALL report that the cosmetic
surface was inferred.

#### Scenario: Declared cosmetic surface is used

- **WHEN** a part declares a `show_face` direction
- **THEN** the visual score's cosmetic-face-down reward is computed against that declared
  direction

#### Scenario: Cosmetic surface is inferred when undeclared

- **WHEN** a part has no declared cosmetic surface
- **THEN** the visual score is computed against a geometry-inferred cosmetic surface and the
  result reports that the direction was inferred

### Requirement: Optimization mode is selectable at the tool boundary

The orientation tool SHALL accept the requested optimization mode (`strength`,
`min_support`, `visual_quality`) as an explicit input, defaulting to `strength` when
unspecified, so the design phase and the re-runnable build script select the same objective
deterministically.

#### Scenario: Mode passed to the tool drives selection

- **WHEN** the orientation tool is invoked with `visual_quality`
- **THEN** the recommended orientation is the one selected under the visual-quality ordering,
  and the result records the active mode

#### Scenario: Unspecified mode defaults to strength

- **WHEN** the orientation tool is invoked without a mode
- **THEN** it selects under the `strength` ordering
