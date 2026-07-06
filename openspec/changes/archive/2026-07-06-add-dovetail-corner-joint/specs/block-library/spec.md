## MODIFIED Requirements

### Requirement: Interface type vocabulary is a closed set
The system SHALL enforce that all interface `type` values in `inventory.json` belong to the
following closed set:

`face_mount`, `screw_hole`, `snap_hook`, `snap_socket`, `axis`, `pin`, `socket`, `slot`,
`port_cutout`, `sliding_interface`, `nut_trap`, `joint_axis`, `ball`, `ball_socket`,
`finger`, `mortise`, `tenon`, `dowel`, `seam`, `union`, `dovetail_corner`

The vocabulary SHALL be enforced identically by the inventory JSON Schema `type` enum and the
inventory validator, so the two agree on the accepted set. The set SHALL NOT include the retired
`hinge_axis` token (superseded by `joint_axis`).

#### Scenario: Valid interface type
- **WHEN** an inventory entry declares `"type": "screw_hole"`
- **THEN** inventory loads without error

#### Scenario: nut_trap interface type accepted
- **WHEN** an inventory entry declares `"type": "nut_trap"`
- **THEN** inventory loads without error

#### Scenario: sliding_interface type accepted
- **WHEN** an inventory entry declares `"type": "sliding_interface"`
- **THEN** inventory loads without error

#### Scenario: seam interface type accepted
- **WHEN** an inventory entry declares `"type": "seam"`
- **THEN** inventory loads without error

#### Scenario: union interface type accepted
- **WHEN** an inventory entry declares `"type": "union"`
- **THEN** inventory loads without error

#### Scenario: joint_axis interface type accepted
- **WHEN** an inventory entry declares `"type": "joint_axis"`
- **THEN** inventory loads without error

#### Scenario: dovetail_corner interface type accepted
- **WHEN** an inventory entry declares `"type": "dovetail_corner"`
- **THEN** inventory loads without error

#### Scenario: Retired hinge_axis token is rejected
- **WHEN** an inventory entry declares `"type": "hinge_axis"`
- **THEN** inventory validation raises an error naming the block and the invalid type

#### Scenario: Invalid interface type
- **WHEN** an inventory entry declares `"type": "glue_tab"` (not in vocabulary)
- **THEN** inventory validation raises an error naming the block and the invalid type
