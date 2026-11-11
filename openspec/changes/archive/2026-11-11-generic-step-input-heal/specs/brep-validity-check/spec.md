## MODIFIED Requirements

### Requirement: Grader-equivalent mesh gate on every wrapper run

For each body with no BRepCheck statuses, the shim SHALL write the body to STEP, read it back, and tessellate it the way the CADGenBench validity gate does. The deflection is 0.001 x the tolerance-enlarged bbox diagonal, clamped to [0.005, 0.5] mm, and it escalates through divisors (1, 4, 16, 32). Faces SHALL be stitched by shared-edge polygon indices and BRep vertices, never by a coordinate weld. Before stitching, each edge's polygon-on-triangulation SHALL be checked against the edge's BRep vertices: its first and last nodes SHALL lie within the deflection of `FirstVertex` and `LastVertex` respectively, the grader's "edge endpoint node is N mm from the vertex" check. If no rung yields a closed, edge-manifold, consistently wound mesh without pinch vertices or endpoint mismatches, the body's entry in `brep_check.json` SHALL be one `"Mesh: <reason>"` string, and `--deliver` export SHALL be skipped. The wrapper SHALL map that entry to one blocking `invalid_mesh` error (union-attributed, `success: false` with or without `--strict`).

#### Scenario: BRep-valid body that does not mesh closed
- **WHEN** a result passes BRepCheck but its STEP tessellates with open edges (e.g. coincident faces left by a `clean=False` boolean)
- **THEN** the wrapper emits `success: false` and one `invalid_mesh` error naming the open-edge count

#### Scenario: Edge polygon does not reach its vertex
- **WHEN** a body's STEP tessellates with an edge polygon whose end node is farther than the deflection from the edge's vertex (CADGenBench 206 after an unconditional ShapeFix heal)
- **THEN** `mesh_gate_error` returns a reason naming the vertex distance, and the wrapper emits one `invalid_mesh` error

#### Scenario: Ordinary part
- **WHEN** a script's result is a filleted box with a hole
- **THEN** no `invalid_mesh` error is added
