## ADDED Requirements

### Requirement: Bridge detection gates regions in bulk
`overhang_regions` SHALL evaluate the bridge angle gate for all regions with one vectorized pass and SHALL invoke the per-region bridge analysis only for regions that pass it, and bridge analysis SHALL NOT compute a convex hull or a row-wise `np.unique` for regions that fail the gate.

#### Scenario: Results unchanged
- **WHEN** `overhang_regions`, `overhang_metrics` or `support_cost` runs on any mesh
- **THEN** each region's `bridge` flag and area, and the resulting costs, are identical to those produced before the change

#### Scenario: Failing regions skip geometry work
- **WHEN** a region's area-weighted mean overhang angle is below `BRIDGE_MIN_DEG`
- **THEN** it is reported with `bridge` false without oriented-bounds or boundary-edge computation
