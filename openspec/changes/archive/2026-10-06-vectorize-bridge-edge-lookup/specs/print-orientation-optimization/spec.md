## ADDED Requirements

### Requirement: Pose-invariant and per-pose shared data is computed once
`optimize_orientation` SHALL compute face areas once on the base mesh and reuse them for every candidate pose, and SHALL compute each pose's bed-contact mask once and share it among the support, incline and stability metrics.

#### Scenario: Scores unchanged
- **WHEN** `optimize_orientation` runs on any mesh and mode
- **THEN** every candidate's scores and the chosen orientation are identical to those produced before the change

#### Scenario: Bed mask not recomputed
- **WHEN** one candidate pose is scored
- **THEN** `bed_contact_mask` is evaluated once for that pose
