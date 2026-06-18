## MODIFIED Requirements

### Requirement: Inventory schema permits the taxonomy fields
`blocks/inventory_schema.json` SHALL allow optional `motion`, `reversible`, and
`carries` properties on inventory items, and SHALL include `hinge_axis`, `ball`,
`ball_socket`, `finger`, `mortise`, `tenon`, `dowel`, and `seam` in the interface
`type` enum. Existing entries SHALL continue to validate without modification.

#### Scenario: Existing entries still validate after schema change
- **WHEN** the current `blocks/inventory.json` is validated against the updated schema
- **THEN** validation SHALL pass with no errors

#### Scenario: New taxonomy fields validate
- **WHEN** an entry with `motion: hinge`, `reversible: false`, and a non-empty
  `carries` array is validated
- **THEN** validation SHALL pass

#### Scenario: seam interface type validates
- **WHEN** an entry declares a single interface of `type: seam`
- **THEN** validation SHALL pass
