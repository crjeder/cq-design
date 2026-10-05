## ADDED Requirements

### Requirement: Ray-cast pre-filtering does not change reported thickness
Any optimization that restricts which triangles a thickness ray is tested against (such as a facing or in-front half-space filter) SHALL produce the same per-face thickness as testing every triangle, for watertight meshes, within floating-point tolerance. The wrapper JSON contract and region fields SHALL be unchanged.

#### Scenario: Filtered and unfiltered casts agree
- **WHEN** the thickness of every sampled face of a watertight part is computed with the pre-filter and with the unfiltered cast
- **THEN** the two thickness arrays are equal within tolerance

#### Scenario: Thin-region output is unchanged
- **WHEN** the existing thin-interface fixtures are measured after the change
- **THEN** the reported regions, thicknesses, and orientations match the previous results
