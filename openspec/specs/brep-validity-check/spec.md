# brep-validity-check Specification

## Purpose
TBD - created by archiving change step-import-repair. Update Purpose after archive.
## Requirements
### Requirement: BRepCheck on every wrapper run

On every `run_cadquery_model.py` run that produces a `result`, the model shim SHALL run `BRepCheck_Analyzer` on each result body: the single `Workplane`, or each value of a `dict` result other than the `keep_out` key. It SHALL write the non-`NoError` statuses of every solid, shell, face, edge and vertex, as `"<Solid|Shell|Face|Edge|Vertex>: <BRepCheck status name>"`, to `brep_check.json` in the run's temp dir, keyed by union id (the script stem for a single body). It SHALL skip `--deliver` export when any body has statuses.

#### Scenario: Valid body
- **WHEN** a script's result is a valid box
- **THEN** `brep_check.json` maps the stem to an empty list and the run adds no error

#### Scenario: Multi-union
- **WHEN** `result` is `{"base": ..., "lid": ...}` and only `lid` is invalid
- **THEN** only `lid` has statuses in `brep_check.json`

### Requirement: Invalid BRep is a blocking structured error

For each body with statuses, the wrapper SHALL add one error of type `invalid_brep`. Its `message` SHALL list the de-duplicated statuses, attributed to the union as other per-union errors are. Its `hint` SHALL point at the operation that produced the body (the last boolean or fillet) or at `blocks.import_solid` for an imported file. The run SHALL report `success: false`, whether or not `--strict` is set. The JSON contract keys SHALL be unchanged.

#### Scenario: Invalid result
- **WHEN** a script's result contains a face with a self-intersecting wire
- **THEN** the wrapper emits `success: false` and one `invalid_brep` error whose message contains `Face: BRepCheck_UnorientableShape` or the actual status

#### Scenario: Shim wrote no sidecar
- **WHEN** the script sets no `result`, so the shim checks nothing
- **THEN** the wrapper adds no `invalid_brep` error


### Requirement: Grader-equivalent mesh gate on every wrapper run

For each body with no BRepCheck statuses, the shim SHALL write the body to STEP, read it back, and tessellate it the way the CADGenBench validity gate does. The deflection is 0.001 x the tolerance-enlarged bbox diagonal, clamped to [0.005, 0.5] mm, and it escalates through divisors (1, 4, 16, 32). Faces SHALL be stitched by shared-edge polygon indices and BRep vertices, never by a coordinate weld. If no rung yields a closed, edge-manifold, consistently wound mesh without pinch vertices, the body's entry in `brep_check.json` SHALL be one `"Mesh: <reason>"` string, and `--deliver` export SHALL be skipped. The wrapper SHALL map that entry to one blocking `invalid_mesh` error (union-attributed, `success: false` with or without `--strict`).

#### Scenario: BRep-valid body that does not mesh closed
- **WHEN** a result passes BRepCheck but its STEP tessellates with open edges (e.g. coincident faces left by a `clean=False` boolean)
- **THEN** the wrapper emits `success: false` and one `invalid_mesh` error naming the open-edge count

#### Scenario: Ordinary part
- **WHEN** a script's result is a filleted box with a hole
- **THEN** no `invalid_mesh` error is added
