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

### Requirement: Score each candidate on bed-stability

For each candidate orientation the system SHALL compute a **stability** outcome: whether the
posed mesh, resting at that candidate orientation, will stay put on the bed under gravity
rather than tip over. A candidate's bed-contact footprint SHALL be the set of vertices of the
faces already classified as bed contact for that candidate (within the first-layer-height
band of the lowest point). A candidate SHALL be marked unstable when its bed-contact
footprint has fewer than 3 distinct XY points (a point or edge/knife-edge contact cannot form
a resting polygon). Otherwise a candidate SHALL be marked stable when the mesh's center of
mass, projected onto the bed plane (XY), falls within the convex hull of the footprint, and
unstable when it falls outside.

#### Scenario: Point or edge contact is always unstable

- **WHEN** a candidate orientation's bed-contact footprint has fewer than 3 distinct XY
  points
- **THEN** the candidate is marked unstable regardless of its support or strength scores

#### Scenario: Center of mass within the footprint hull is stable

- **WHEN** a candidate orientation's bed-contact footprint has 3 or more distinct XY points
  and the posed mesh's center of mass projects within the convex hull of that footprint
- **THEN** the candidate is marked stable

#### Scenario: Center of mass outside the footprint hull is unstable

- **WHEN** a candidate orientation's posed center of mass projects outside the convex hull of
  its bed-contact footprint
- **THEN** the candidate is marked unstable

### Requirement: Select orientation by the requested optimization mode

The system SHALL select the recommended orientation according to a requested optimization
mode, one of `strength`, `min_support`, `visual_quality`, or `min_build_height` (default
`strength`). Before applying the mode's ordering, the system SHALL restrict the candidate set
to stable candidates (per the bed-stability requirement) whenever at least one candidate is
stable; when no candidate is stable, the system SHALL fall back to the full candidate set so
a recommendation is still produced. Within the (possibly restricted) candidate set, each mode
SHALL apply a deterministic lexicographic ordering with a tolerance band on the primary key
so near-ties fall through to the next key:

- `strength`: primary best strength (higher), ties within the strength band broken by least
  support, then most bed contact. (Unchanged from prior behavior.)
- `min_support`: primary least support (lower), ties within a support band broken by best
  strength, then most bed contact.
- `visual_quality`: primary best visual score (higher), ties within a visual band broken by
  best strength, then least support.
- `min_build_height`: primary least build height (lower), ties within a build-height band
  broken by best strength, then least support.

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

#### Scenario: An unstable near-point-balance candidate loses to a stable flat face

- **WHEN** the mode is `strength`, the part has no declared load (or a declared
  `load_type=compression`) so strength is orientation-neutral, one candidate rests flat with
  full bed contact but a support cost from small features, and another candidate balances on
  a corner or edge with near-zero support cost but an unstable (fewer than 3 contact points,
  or center-of-mass-outside-hull) footprint
- **THEN** the flat, stable candidate is selected even though its support cost is higher

#### Scenario: All candidates unstable falls back to the full set

- **WHEN** every candidate orientation for a mesh is marked unstable (no flat resting face
  exists)
- **THEN** selection proceeds over the full candidate set exactly as it did before the
  stability gate existed, and a recommendation is still produced

### Requirement: Emit the chosen orientation transform with rationale

The system SHALL emit, per union, the recommended print orientation as a rotation
transform (compatible with the `placement.py` rotation convention), together with the
strength, support, visual, and stability outcome for the chosen candidate, the active
optimization mode, and a human-readable rationale that names the mode and explains why the
pose won under it. When the stability gate excluded one or more unstable candidates from
consideration, the rationale SHALL note that exclusion. This output SHALL be distinct from
the union's assembled-frame `placement`.

The orientation tool SHALL accept an optional source-script path identifying the part
script whose authored-frame geometry produced the mesh being scored. When supplied, the
result SHALL carry that script's provenance stamp (`source_script_hash`) so the result is
self-describing about which script version it was computed from. When omitted, the result
SHALL carry no such stamp, and a consumer comparing against it SHALL treat the absence as
unknown provenance, not a mismatch.

#### Scenario: Result carries transform, scores, and mode

- **WHEN** orientation optimization completes for a union
- **THEN** the result contains the rotation transform, the strength score, the support
  score, the visual score, whether the chosen candidate is stable, the active `optimize_for`
  mode, and a rationale string, and does not overwrite the union's `placement`

#### Scenario: Rationale notes when unstable candidates were excluded

- **WHEN** at least one candidate was excluded from selection by the stability gate
- **THEN** the rationale string mentions that unstable candidates were excluded from
  consideration

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
