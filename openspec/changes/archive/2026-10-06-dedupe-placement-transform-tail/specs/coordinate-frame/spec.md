## ADDED Requirements

### Requirement: Placement appliers share one kernel transform path
`placement.apply_cq` and `placement.apply_matrix` SHALL apply their transform to each shape through a single shared OCCT-level routine that does not call `Workplane.rotate`, `Workplane.translate`, or `Shape.copy`, so the cq_warehouse deepcopy patch is never entered.

#### Scenario: Placement-shaped transform avoids the patched copy
- **WHEN** `apply_cq` is called with a non-empty placement while the cq_warehouse `Shape` patch is active
- **THEN** the result is positioned per `to_matrix` and `Shape.copy` is not entered

#### Scenario: Matrix transform matches placement transform
- **WHEN** `apply_matrix` is called with `to_matrix(placement)` and `apply_cq` with the same `placement`
- **THEN** both results have the same geometry
