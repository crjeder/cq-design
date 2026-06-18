# Block Library

## Purpose

Defines requirements for the `blocks/` package: a machine-readable inventory of reusable CadQuery geometry primitives and the rules for how the orchestrator selects and injects them into per-part prompts.

## Requirements

### Requirement: Block inventory is a machine-readable JSON catalog
The system SHALL provide `blocks/inventory.json` containing an array of block descriptors. Each descriptor SHALL include:

- `name` (string, required, unique, kebab-case)
- `module` (string, required, Python dotted path, e.g. `blocks.fasteners`)
- `function` (string, required, Python function name)
- `use` (string, required, plain-English description of the block's purpose and when to use it)
- `params` (object, required, parameter name → unit string)
- `dimensions` (array of 3 numbers or null if variable, in mm [w, d, h])
- `interfaces` (array of interface descriptors, may be empty)

Each interface descriptor SHALL include:
- `type` (string, required, from the closed vocabulary)
- `orientation` (string, required, e.g. `"+Z"`, `"-Y"`)
- `origin` (array of 3 numbers, required, in block-local coordinates mm)

#### Scenario: Block lookup by name
- **WHEN** the orchestrator looks up `"pcb_standoff"` in the inventory
- **THEN** it receives the full descriptor including params, dimensions, and interfaces

#### Scenario: Unknown block name in plan
- **WHEN** `BUILD_PLAN.json` references a block name not present in `inventory.json`
- **THEN** plan validation fails with an error listing the unknown name

---

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

---

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

---

### Requirement: Part prompt includes only blocks relevant to that part
The system SHALL generate per-part prompts that embed only the block descriptors listed in the part's `blocks_needed` field, not the full inventory.

#### Scenario: Part with two blocks
- **WHEN** a part's `blocks_needed` is `["fillet_box", "pcb_standoff"]`
- **THEN** the generated part prompt contains only those two block descriptors

#### Scenario: Part with no blocks
- **WHEN** a part's `blocks_needed` is empty
- **THEN** the generated part prompt contains no block descriptor section and instructs the LLM to use raw CadQuery primitives

---

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
