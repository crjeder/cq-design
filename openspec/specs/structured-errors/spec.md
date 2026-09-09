# Structured Errors

## Purpose

Defines requirements for structured error reporting from `run_cadquery_model.py`: JSON-encoded error objects with typed categories, actionable hints, and location information, replacing raw OCC tracebacks as the primary error channel.
## Requirements
### Requirement: Wrapper emits structured errors in JSON, not raw tracebacks
The wrapper (`run_cadquery_model.py`) SHALL populate a top-level `errors` array in its JSON output. Each entry SHALL be an object with at minimum `type` (string), `message` (string), and `hint` (string). Raw OCC tracebacks SHALL remain available in `stderr` for debugging but SHALL NOT be the primary error channel.

#### Scenario: Script succeeds with no geometry errors
- **WHEN** the model script exits 0 and produces valid watertight geometry
- **THEN** `errors` array is empty

#### Scenario: Script raises an OCC exception
- **WHEN** the script raises `Standard_ConstructionError`
- **THEN** `errors` contains one entry with `type: "occ_exception"`, the exception class name and message in `message`, and a generic hint in `hint`; raw traceback is in `stderr`

---

### Requirement: Non-manifold edges are reported with face identifiers
When trimesh detects non-manifold edges, the wrapper SHALL report each affected edge with the hash IDs of the two adjacent faces and the gap distance in mm.

#### Scenario: Boolean gap produces non-manifold edge
- **WHEN** a boolean subtraction leaves a 0.003 mm gap
- **THEN** `errors` contains an entry with `type: "non_manifold_edge"`, `location` containing face hash IDs, `gap_mm: 0.003`, and a hint referencing the epsilon-extension fix

#### Scenario: Watertight mesh
- **WHEN** trimesh reports the mesh as watertight with no non-manifold edges
- **THEN** no `non_manifold_edge` entry appears in `errors`

---

### Requirement: Dimension mismatches against plan are reported as structured errors
When the orchestrator provides expected dimensions (from `BUILD_PLAN.json`) to the wrapper, the wrapper SHALL compare actual bounding-box values and emit a `dimension_mismatch` error for any axis where the delta exceeds the tolerance.

#### Scenario: X-axis too small
- **WHEN** expected `w_mm: 50` but actual bounding box X is 43.1 mm
- **THEN** `errors` contains `type: "dimension_mismatch"`, `axis: "x"`, `actual_mm: 43.1`, `expected_mm: 50.0`, `delta_mm: -6.9`

---

### Requirement: Thin wall violations are reported with location
When DFM analysis detects walls below `constraints.wall_min_mm`, the wrapper SHALL report the approximate location (face centroid) and measured thickness.

#### Scenario: 0.8 mm wall with 1.2 mm minimum
- **WHEN** a face pair is estimated at 0.8 mm separation and `wall_min_mm` is 1.2
- **THEN** `errors` contains `type: "thin_wall"`, `thickness_mm: 0.8`, `min_mm: 1.2`, and approximate face centroid coordinates

---

### Requirement: Known OCC exception classes map to actionable hints
The wrapper SHALL maintain a translation table mapping known OCC exception class
names to a distinct structured-error `type` and a specific, actionable hint. At
minimum the following SHALL be covered:

| OCC class | `type` | hint |
|-----------|--------|------|
| `Standard_ConstructionError` | `construction_error` | "geometry construction failed -- check that boolean bodies overlap and no faces are coincident" |
| `BRep_API` (command not done) | `command_not_done` | "boolean operation failed -- ensure inner body extends at least 0.01 mm past outer boundary" |
| `StdFail_NotDone` | `fillet_failure` | "operation left incomplete -- fillet radius may exceed adjacent face dimension; reduce radius" |
| `Standard_NullObject` | `null_object` | "referenced a shape that does not exist -- check selector strings and workplane offsets" |
| `Standard_OutOfRange` | `index_out_of_range` | "index out of range -- check pushPoints list or loop bounds" |
| `Standard_TypeMismatch` | `type_mismatch` | "wrong shape type for this operation -- verify the workplane and selector are targeting the correct geometry" |

An OCC exception class not in this table SHALL still be reported with
`type: "occ_exception"` and the generic fallback hint. Every entry, mapped or
not, SHALL carry the raw exception class name in `occ_class`.

#### Scenario: Known OCC exception
- **WHEN** the script raises `StdFail_NotDone`
- **THEN** `errors` contains one entry with `type: "fillet_failure"`,
  `occ_class: "StdFail_NotDone"`, and the specific hint for that class

#### Scenario: Command-not-done boolean failure
- **WHEN** the script raises `BRep_API`
- **THEN** `errors` contains one entry with `type: "command_not_done"` and the
  boolean-overlap hint

#### Scenario: Unknown OCC exception
- **WHEN** the script raises an OCC exception not in the translation table
- **THEN** `errors` contains `type: "occ_exception"` with `occ_class` set to
  the raw class name, its message, and the generic hint "check CadQuery
  documentation for this exception class"

---

### Requirement: Runtime verify-helper failures map to typed errors

The wrapper (`run_cadquery_model.py`) SHALL translate a `RuntimeError` raised by the
runtime boolean-verify helper (silent-boolean, feature-bounds-overflow, or workplane-
drift) into a structured `errors` entry with a specific `type` rather than the generic
`occ_exception` fallback. A silent-boolean failure SHALL use `type: "silent_boolean"`; a
feature-bounds overflow SHALL use `type: "feature_overflow"`; a workplane-origin drift
SHALL use `type: "workplane_drift"`. Each entry SHALL include the feature/workplane
`label` from the helper, a `message` reproducing the helper's detail, and a `hint`
directing the fix (reposition the tool so it overlaps / constrain the feature within the
body / re-anchor the workplane origin). The raw traceback SHALL remain in `stderr`.

#### Scenario: Silent cut raises during construction

- **WHEN** a wrapped `.cut()` produces no change and the helper raises `RuntimeError`
- **THEN** `errors` contains one entry with `type: "silent_boolean"`, the feature
  `label`, and a hint about the tool not overlapping the body; the raw traceback is in
  `stderr`

#### Scenario: Feature overflow raises during construction

- **WHEN** the bounds helper raises `RuntimeError` for a feature extending past the body
- **THEN** `errors` contains one entry with `type: "feature_overflow"`, the feature
  `label`, the per-axis overflow in `message`, and a hint about constraining the feature

#### Scenario: Workplane drift raises during construction

- **WHEN** the workplane check raises `RuntimeError` for an origin that drifted past the
  tolerance
- **THEN** `errors` contains one entry with `type: "workplane_drift"`, the `label`,
  expected vs. actual origin in `message`, and a hint about re-anchoring the workplane

#### Scenario: Non-verify RuntimeError is unaffected

- **WHEN** the script raises a `RuntimeError` that did not originate from the verify
  helper
- **THEN** the wrapper does not classify it as `silent_boolean` or `feature_overflow`

### Requirement: Disconnected union bodies are reported as structured errors

The wrapper (`run_cadquery_model.py`) SHALL emit a blocking `disconnected_body` error
when a union body splits into more than one connected component. Each declared union
maps to one rigid printed body and is therefore expected to tessellate into a single
connected component. The emitted `errors` entry SHALL carry `type:
"disconnected_body"`, the offending `union` id, a
`component_count`, and a `message` listing each component's per-axis bounding range
(`min..max` per axis, not extents, so a gap between two bodies is readable off the
message) and volume, plus a `hint` directing the author to compare those ranges before
adding overlap: non-overlapping ranges mean a body is misplaced and must be moved back,
not merely grown until it touches. The
check SHALL run per union (a single-`Workplane` result is one union with id equal to
the part id; a `dict` result is checked once per union key) and SHALL exclude the
reserved keep-out key.

#### Scenario: Union splits into multiple bodies

- **WHEN** a part's `result` union tessellates into two non-touching solids
- **THEN** `errors` contains one entry with `type: "disconnected_body"`, the `union`
  id, `component_count: 2`, per-component axis ranges and volume in `message`, and a
  hint that orders the placement check ahead of bridging; `success` is `false`

#### Scenario: Message exposes the gap between two non-touching bodies

- **WHEN** a union splits into two solids separated along one axis
- **THEN** the `message` gives each body's `min..max` on all three axes, so the
  separating axis and the size of the gap are readable without a further probe

#### Scenario: Single connected body

- **WHEN** a union tessellates into exactly one connected component
- **THEN** no `disconnected_body` entry appears in `errors`

#### Scenario: Multi-union part checked per union

- **WHEN** a `dict` result declares two unions, each a single connected body
- **THEN** no `disconnected_body` entry appears, even though the part has two separate
  bodies, because each declared union is independently one component

#### Scenario: Keep-out zone excluded

- **WHEN** a `dict` result carries the reserved keep-out key alongside union bodies
- **THEN** the keep-out entry is not subjected to the connected-component check

