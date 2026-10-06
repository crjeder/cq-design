## ADDED Requirements

### Requirement: 3MF writer welds vertices and reports non-manifold edges
The 3MF writers in `exporters/threemf_multi.py` SHALL weld tessellation vertices that coincide to six decimal places into one shared index per physical vertex, keeping first-seen vertex order, so every interior edge of a closed solid is used by exactly two triangles. `write_named_3mf` and `write_single_3mf` SHALL return the number of edges used by other than two triangles in the written index topology, computed from the in-memory welded arrays without re-reading the file. `count_nonmanifold_edges(path)` SHALL remain available as an independent from-file check.

#### Scenario: Closed solid writes zero non-manifold edges
- **WHEN** `write_named_3mf` is called with a closed box
- **THEN** it returns 0
- **AND** `count_nonmanifold_edges` on the written file also returns 0

#### Scenario: Deliverable guard uses the writer's count
- **WHEN** `deliverables.py` writes `model.3mf`
- **THEN** it raises RuntimeError if the writer's returned count is non-zero
- **AND** it does not re-open the written file to count edges
