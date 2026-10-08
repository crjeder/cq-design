## ADDED Requirements

### Requirement: Pose-invariant geometry is computed once per mesh
`optimize_orientation` SHALL compute triangle centroids and the face-adjacency edge keys once on the base mesh, SHALL derive each pose's centroid z from them by the pose's rotation and translation, and SHALL share that z between the bed-contact mask and bridge detection.

#### Scenario: Scores unchanged
- **WHEN** `optimize_orientation` runs on any mesh and mode
- **THEN** every candidate's scores and the chosen orientation are identical to those produced before the change

#### Scenario: No per-pose centroid recomputation
- **WHEN** one candidate pose is scored
- **THEN** triangle centroids are not recomputed from the posed mesh's vertices
