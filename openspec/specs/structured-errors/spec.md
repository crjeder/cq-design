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
The wrapper SHALL maintain a translation table mapping known OCC exception class names to specific, actionable hints. At minimum the following SHALL be covered:

| OCC class | hint |
|-----------|------|
| `Standard_ConstructionError` | "geometry construction failed -- check that boolean bodies overlap and no faces are coincident" |
| `BRep_API` (command not done) | "boolean operation failed -- ensure inner body extends at least 0.01 mm past outer boundary" |
| `StdFail_NotDone` | "operation left incomplete -- fillet radius may exceed adjacent face dimension; reduce radius" |
| `Standard_NullObject` | "referenced a shape that does not exist -- check selector strings and workplane offsets" |

#### Scenario: Known OCC exception
- **WHEN** the script raises `StdFail_NotDone`
- **THEN** `errors` contains the specific hint for that class, not the generic fallback

#### Scenario: Unknown OCC exception
- **WHEN** the script raises an OCC exception not in the translation table
- **THEN** `errors` contains `type: "occ_exception"` with class name, message, and the generic hint "check CadQuery documentation for this exception class"
