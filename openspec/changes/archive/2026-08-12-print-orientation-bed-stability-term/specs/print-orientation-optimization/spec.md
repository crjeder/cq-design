## ADDED Requirements

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

## MODIFIED Requirements

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
