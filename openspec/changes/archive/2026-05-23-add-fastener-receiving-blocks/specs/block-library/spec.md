## MODIFIED Requirements

### Requirement: Interface type vocabulary is a closed set
The system SHALL enforce that all interface `type` values in `inventory.json` belong to the following set:

`face_mount`, `screw_hole`, `snap_hook`, `snap_socket`, `axis`, `pin`, `socket`, `slot`, `port_cutout`, `sliding_interface`, `nut_trap`

(`sliding_interface` was introduced by the dovetail-joint blocks and is now formally registered. `nut_trap` is added for the `hex_nut_trap` block.)

#### Scenario: Valid interface type
- **WHEN** an inventory entry declares `"type": "screw_hole"`
- **THEN** inventory loads without error

#### Scenario: nut_trap interface type accepted
- **WHEN** an inventory entry declares `"type": "nut_trap"`
- **THEN** inventory loads without error

#### Scenario: sliding_interface type accepted
- **WHEN** an inventory entry declares `"type": "sliding_interface"`
- **THEN** inventory loads without error

#### Scenario: Invalid interface type
- **WHEN** an inventory entry declares `"type": "glue_tab"` (not in vocabulary)
- **THEN** inventory validation raises an error naming the block and the invalid type

---

### Requirement: Initial inventory covers at least 10 common blocks
The system SHALL ship `blocks/inventory.json` with at minimum the following blocks:

`fillet_box`, `hollow_box`, `pcb_standoff`, `screw_boss`, `snap_hook_clip`, `snap_socket_receiver`, `port_cutout`, `cable_slot`, `vent_grid`, `alignment_pin`, `alignment_socket`, `dovetail_groove`, `dovetail_tongue`, `heat_set_boss`, `counterbore_hole`, `countersink_hole`, `hex_nut_trap`

Each block SHALL have a corresponding Python implementation in `blocks/`.

#### Scenario: Import and call a block
- **WHEN** a model script imports `from blocks.fasteners import heat_set_boss` and calls it with valid params
- **THEN** it returns a valid CadQuery `Workplane` object without error

#### Scenario: Import and call hex_nut_trap
- **WHEN** a model script imports `from blocks.fasteners import hex_nut_trap` and calls it with valid params
- **THEN** it returns a valid CadQuery `Workplane` object without error
