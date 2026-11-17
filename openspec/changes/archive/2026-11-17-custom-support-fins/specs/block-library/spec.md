## ADDED Requirements

### Requirement: Inventory lists the breakaway fin block
`blocks/inventory.json` SHALL contain a `breakaway_fin` descriptor with `kind: "block"`,
`module: "blocks.supports"`, `function: "breakaway_fin"`, a `probes` function, and
`params` covering height, length, layer height, tine width, wall thickness, standoff and
tine overlap. The block SHALL be importable as `from blocks import breakaway_fin`.

#### Scenario: Lookup by name
- **WHEN** the orchestrator looks up `"breakaway_fin"` in the inventory
- **THEN** it receives a descriptor that passes inventory schema validation

#### Scenario: Package import
- **WHEN** a part script runs `from blocks import breakaway_fin`
- **THEN** the import succeeds
