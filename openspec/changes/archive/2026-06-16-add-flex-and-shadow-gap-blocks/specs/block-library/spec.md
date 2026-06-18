## MODIFIED Requirements

### Requirement: Interface type vocabulary is a closed set
The system SHALL enforce that all interface `type` values in `inventory.json` belong to the following set:

`face_mount`, `screw_hole`, `snap_hook`, `snap_socket`, `axis`, `pin`, `socket`, `slot`, `port_cutout`, `sliding_interface`, `nut_trap`, `seam`

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

#### Scenario: Invalid interface type
- **WHEN** an inventory entry declares `"type": "glue_tab"` (not in vocabulary)
- **THEN** inventory validation raises an error naming the block and the invalid type
