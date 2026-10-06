## ADDED Requirements

### Requirement: Bridge detection avoids per-edge Python work
`_is_bridge` SHALL resolve region boundary edges to their neighboring faces and accumulate anchored length per rectangle side with vectorized array operations, and SHALL NOT build a Python mapping over all mesh edges per `overhang_regions` call.

#### Scenario: Results unchanged
- **WHEN** `overhang_regions`, `overhang_metrics` or `support_cost` runs on any mesh
- **THEN** each region's `bridge` flag, area and the resulting costs are identical to those produced before the change

#### Scenario: Setup cost does not scale in Python per edge
- **WHEN** a mesh with 100,000 or more adjacency edges is analyzed
- **THEN** the edge-to-face lookup is built from sorted array keys without a per-edge Python loop or dict
