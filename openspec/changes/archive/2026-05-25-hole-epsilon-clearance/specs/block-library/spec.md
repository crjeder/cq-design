## MODIFIED Requirements

### Requirement: Subtractive blocks overcut by epsilon
All block functions that return solids intended for `.cut()` operations (subtractive blocks) SHALL extrude by `depth + _EPS` on the axis that exits the far face of the material, where `_EPS` is a module-level constant with a value of `1e-4` mm. This applies to: `counterbore_hole`, `countersink_hole`, `hex_nut_trap`, `alignment_socket`, `snap_socket_receiver` (fasteners.py), and `port_cutout`, `cable_slot`, `vent_grid` (connectors.py). Lateral dimensions (width, diameter) SHALL NOT be affected.

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
