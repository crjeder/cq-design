## ADDED Requirements

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

`face_mount`, `screw_hole`, `snap_hook`, `snap_socket`, `axis`, `pin`, `socket`, `slot`, `port_cutout`

#### Scenario: Valid interface type
- **WHEN** an inventory entry declares `"type": "screw_hole"`
- **THEN** inventory loads without error

#### Scenario: Invalid interface type
- **WHEN** an inventory entry declares `"type": "glue_tab"` (not in vocabulary)
- **THEN** inventory validation raises an error naming the block and the invalid type

---

### Requirement: Initial inventory covers at least 10 common blocks
The system SHALL ship `blocks/inventory.json` with at minimum the following blocks:

`fillet_box`, `hollow_box`, `pcb_standoff`, `screw_boss`, `snap_hook_clip`, `snap_socket_receiver`, `port_cutout`, `cable_slot`, `vent_grid`, `alignment_pin`, `alignment_socket`

Each block SHALL have a corresponding Python implementation in `blocks/`.

#### Scenario: Import and call a block
- **WHEN** a model script imports `from blocks.fasteners import pcb_standoff` and calls it with valid params
- **THEN** it returns a valid CadQuery `Workplane` object without error

---

### Requirement: Part prompt includes only blocks relevant to that part
The system SHALL generate per-part prompts that embed only the block descriptors listed in the part's `blocks_needed` field, not the full inventory.

#### Scenario: Part with two blocks
- **WHEN** a part's `blocks_needed` is `["fillet_box", "pcb_standoff"]`
- **THEN** the generated part prompt contains only those two block descriptors

#### Scenario: Part with no blocks
- **WHEN** a part's `blocks_needed` is empty
- **THEN** the generated part prompt contains no block descriptor section and instructs the LLM to use raw CadQuery primitives
