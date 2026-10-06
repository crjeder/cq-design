## ADDED Requirements

### Requirement: Local thickness cast is batched and implementation-independent
The geometry-level local thickness field SHALL be computed by a single batched ray query over all sampled faces rather than a per-ray loop over the mesh triangles, and SHALL yield the same per-face thickness as the exhaustive reference cast (nearest forward hit on a triangle whose outward normal points along the ray, beyond the minimum distance).

#### Scenario: Batched cast matches the exhaustive reference
- **WHEN** the thickness is computed for every face of a mesh with both the batched cast and the exhaustive all-triangle reference
- **THEN** the per-face thickness values agree within floating-point tolerance

#### Scenario: Thin-region output is unchanged
- **WHEN** `measure_stl.measure` runs on a part with a thin wall
- **THEN** the reported `thin_regions` (thickness, orientation, location, nearest feature) are the same as before the batching change
