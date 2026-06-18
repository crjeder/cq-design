## MODIFIED Requirements

### Requirement: Initial inventory covers at least 10 common blocks
The system SHALL ship `blocks/inventory.json` with at minimum the following blocks:

`fillet_box`, `hollow_box`, `pcb_standoff`, `screw_boss`, `snap_hook_clip`, `snap_socket_receiver`, `port_cutout`, `cable_slot`, `vent_grid`, `alignment_pin`, `alignment_socket`, `heat_set_boss`, `socket_head_cap_screw`, `hex_head_screw`, `hex_nut`, `dovetail_groove`, `dovetail_tongue`, `counterbore_hole`, `countersink_hole`, `hex_nut_trap`, `teardrop_bore`, `teardrop_post`

Each block SHALL have a corresponding Python implementation in `blocks/`.

#### Scenario: Import and call a block
- **WHEN** a model script imports `from blocks.fasteners import pcb_standoff` and calls it with valid params
- **THEN** it returns a valid CadQuery `Workplane` object without error

#### Scenario: Teardrop bore is present in the inventory
- **WHEN** the inventory is loaded
- **THEN** it contains a `teardrop_bore` descriptor whose `module` is `blocks.connectors`

#### Scenario: Teardrop post is present in the inventory
- **WHEN** the inventory is loaded
- **THEN** it contains a `teardrop_post` descriptor whose `module` is `blocks.connectors`
