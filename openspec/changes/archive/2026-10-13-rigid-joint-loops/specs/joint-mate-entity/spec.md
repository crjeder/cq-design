## MODIFIED Requirements

### Requirement: The mate graph is validated as a single tree rooted at `root_part`

`plan.py validate` SHALL treat each `joints` entry as an edge between its two members' parts. Every part named in some `joints` entry SHALL be reachable from `root_part`; poses are derived along a BFS spanning tree of that graph. An edge that is not on the spanning tree (a **closure edge**, including a second joint between an already-linked pair of parts) is permitted only when its block's inventory descriptor carries no `dof` (a **rigid** joint). A closure edge whose block carries a `dof` SHALL be rejected as a **conflicting mate path** -- closed kinematic loops are out of scope, the same boundary as the `kinematics` array. A part named in some `joints` entry that is NOT reachable from `root_part` SHALL be rejected as **unanchored**. A part reachable from `root_part` via the mate chain that ALSO declares its own `placement` SHALL be rejected as **double-anchored**; `root_part` itself is exempt. The spanning tree SHALL be the BFS from `root_part` in `joints` array order, so the derived poses are deterministic.

#### Scenario: A part disconnected from root_part is rejected
- **WHEN** a `joints` entry links two parts neither of which is `root_part` nor reachable from it
- **THEN** plan validation fails, reporting both parts as unanchored

#### Scenario: A loop of kinematic joints is rejected
- **WHEN** three `pin_hinge` `joints` entries connect parts A-B, B-C, and C-A, forming a loop
- **THEN** plan validation fails, reporting a conflicting mate path

#### Scenario: A loop of rigid joints is accepted
- **WHEN** four `dovetail_corner_joint` entries connect wall_a-wall_c, wall_c-wall_b, wall_b-wall_d, wall_d-wall_a with consistent docks
- **THEN** plan validation passes, and the walls' poses are derived along the BFS tree from `root_part`

#### Scenario: A mate-chain part with its own placement is rejected
- **WHEN** a part reachable from `root_part` via one `joints` entry also declares its own `placement`
- **THEN** plan validation fails: the part is double-anchored

#### Scenario: root_part's own placement is not double-anchoring
- **WHEN** `root_part` declares a `placement` and is also named in a `joints` entry's members
- **THEN** plan validation passes: `root_part`'s `placement` is its edge into the world, not a conflict

## ADDED Requirements

### Requirement: A rigid loop's closure edges SHALL agree with the derived poses

For each closure edge (a rigid `joints` entry not on the spanning tree) linking member A on part P and member B on part Q, `plan.py validate` SHALL compute the residual `inverse(world_pose(Q) . dock_B) . (world_pose(P) . dock_A)`, with `world_pose` the pose derived along the spanning tree (`root_part`'s own `placement`, or identity). If the residual translation exceeds 0.01 mm or its rotation exceeds 0.01 degrees, validation SHALL fail with an error naming the `joint_id`, both parts, and the translation (mm) and rotation (deg) residuals. The check SHALL be evaluated on the docks, not on any clearance offset inside the block's own geometry.

#### Scenario: A consistent rigid loop closes
- **WHEN** a four-part ring of rigid joints has docks that compose to identity around the ring
- **THEN** every closure edge's residual is within tolerance and validation passes

#### Scenario: An inconsistent rigid loop is rejected with the residual
- **WHEN** one dock in the ring is off by 2 mm along X
- **THEN** validation fails, naming the closure edge's `joint_id`, its two parts, and a translation residual of about 2 mm

#### Scenario: A redundant second joint between the same two parts is checked
- **WHEN** two rigid `joints` entries link the same pair of parts and their docks disagree
- **THEN** validation fails with a closure residual error for the second entry

#### Scenario: Pose derivation is unchanged by a closed loop
- **WHEN** a plan with a consistent rigid loop is assembled
- **THEN** `compute_mate_poses` returns the same poses it would for the spanning tree alone
