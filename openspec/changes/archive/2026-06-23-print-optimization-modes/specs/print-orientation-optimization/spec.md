## MODIFIED Requirements

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

#### Scenario: Result carries transform, scores, and mode

- **WHEN** orientation optimization completes for a union
- **THEN** the result contains the rotation transform, the strength score, the support
  score, the visual score, the active `optimize_for` mode, and a rationale string, and does
  not overwrite the union's `placement`

## ADDED Requirements

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
