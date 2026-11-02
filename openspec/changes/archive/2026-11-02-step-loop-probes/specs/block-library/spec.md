## MODIFIED Requirements

### Requirement: Block inventory is a machine-readable JSON catalog
The system SHALL provide `blocks/inventory.json` containing an array of block descriptors
covering blocks, archetype templates and primitives. Each descriptor SHALL include:

- `name` (string, required, unique, kebab-case)
- `kind` (string, required, one of `block`, `template`, `primitive`)
- `module` (string, required, Python dotted path, e.g. `blocks.fasteners`)
- `function` (string, required, Python function name)
- `probes` (string, required, name of the probe function in the same module)
- `edge_sets` (object, required, edge-set name -> description; may be empty; the
  entry's module provides the set's curves in local coordinates for the finishing pass)
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
- **THEN** it receives the full descriptor including params, dimensions, probes, and
  interfaces

#### Scenario: Unknown block name in plan
- **WHEN** `BUILD_PLAN.json` references a block name not present in `inventory.json`
- **THEN** plan validation fails with an error listing the unknown name

#### Scenario: Descriptor without probes
- **WHEN** an inventory descriptor omits `probes`
- **THEN** inventory schema validation fails naming the descriptor
