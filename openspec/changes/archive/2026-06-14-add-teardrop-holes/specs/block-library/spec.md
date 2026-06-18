## MODIFIED Requirements

### Requirement: Initial inventory covers at least 10 common blocks
The system SHALL ship `blocks/inventory.json` with at minimum the following blocks:

`fillet_box`, `hollow_box`, `pcb_standoff`, `screw_boss`, `snap_hook_clip`, `snap_socket_receiver`, `port_cutout`, `cable_slot`, `vent_grid`, `alignment_pin`, `alignment_socket`, `heat_set_boss`, `socket_head_cap_screw`, `hex_head_screw`, `hex_nut`, `dovetail_groove`, `dovetail_tongue`, `counterbore_hole`, `countersink_hole`, `hex_nut_trap`, `teardrop_bore`

Each block SHALL have a corresponding Python implementation in `blocks/`.

#### Scenario: Import and call a block
- **WHEN** a model script imports `from blocks.fasteners import pcb_standoff` and calls it with valid params
- **THEN** it returns a valid CadQuery `Workplane` object without error

#### Scenario: Teardrop bore is present in the inventory
- **WHEN** the inventory is loaded
- **THEN** it contains a `teardrop_bore` descriptor whose `module` is `blocks.connectors`

### Requirement: Subtractive blocks overcut by epsilon
All block functions that return solids intended for `.cut()` operations (subtractive blocks) SHALL extrude by `depth + _EPS` on the axis that exits the far face of the material, where `_EPS` is a module-level constant with a value of `1e-4` mm. This applies to: `counterbore_hole`, `countersink_hole`, `hex_nut_trap`, `alignment_socket`, `snap_socket_receiver` (fasteners.py), and `port_cutout`, `cable_slot`, `vent_grid`, `teardrop_bore` (connectors.py). Lateral dimensions (width, diameter) SHALL NOT be affected.

#### Scenario: Hole exactly as deep as material thickness cuts clean
- **WHEN** `counterbore_hole` is subtracted from a body whose thickness equals the `depth` argument
- **THEN** the resulting solid is watertight with no coincident faces on the far surface

#### Scenario: Epsilon is not visible to callers
- **WHEN** a caller constructs a subtractive block with a given `depth`
- **THEN** the function signature and return type are identical to before this change; no new parameters are required

#### Scenario: Lateral dimensions unchanged
- **WHEN** `port_cutout(w=9.0, h=3.5, depth=3.0)` is called
- **THEN** the resulting solid has width 9.0 mm and height 3.5 mm, with depth equal to `3.0 + _EPS`

#### Scenario: Epsilon constant defined per module
- **WHEN** `fasteners.py` or `connectors.py` is imported
- **THEN** a module-level `_EPS` constant of value `1e-4` is defined in each module

#### Scenario: Teardrop bore overcuts the exit face
- **WHEN** `teardrop_bore(d=8.0, depth=4.0)` is subtracted from a wall 4.0 mm thick
- **THEN** the resulting solid is watertight with no coincident faces on the bore exit surface
