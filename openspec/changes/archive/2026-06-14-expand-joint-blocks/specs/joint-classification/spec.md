## ADDED Requirements

### Requirement: Joints are classified by motion and reversibility
Every joint inventory entry SHALL be classifiable along two orthogonal axes:
`motion` (the relative movement permitted after assembly) and `reversible` (whether
the joint can be separated non-destructively). `motion` SHALL be one of `rigid`,
`hinge`, or `ball`. `reversible` SHALL be a boolean recording the joint's default fit.

#### Scenario: Hinge is mobile and (pinned) permanent
- **WHEN** the `hinge_leaf` entry with the pinned variant is read
- **THEN** its `motion` SHALL be `hinge` and its `reversible` SHALL be `false`

#### Scenario: Sliding dovetail is rigid and separable
- **WHEN** the `dovetail_tongue` entry is read
- **THEN** its `motion` SHALL be `rigid` and its `reversible` SHALL be `true`

#### Scenario: Press-fit dowel is rigid and permanent
- **WHEN** the `dowel_bore` entry is read with its default (interference) clearance
- **THEN** its `motion` SHALL be `rigid` and its `reversible` SHALL be `false`

### Requirement: Reversibility is set by the clearance fit modifier
Every joint pair SHALL accept a `clearance` parameter where a positive value yields a
separable gap fit and a negative value yields an interference (press) fit. The
geometry SHALL be otherwise unchanged; only the fit dimension changes. The inventory
`reversible` field records the default, not an immutable property.

#### Scenario: Positive clearance separates, negative interferes
- **WHEN** any negative (subtractive) joint member is generated with `clearance > 0`
- **THEN** its mating dimension SHALL be larger than the positive member by `2*clearance`
- **WHEN** the same member is generated with `clearance < 0`
- **THEN** its mating dimension SHALL be smaller than the positive member, producing interference

### Requirement: Joints declare the load directions they carry across the seam
A joint inventory entry SHALL be permitted to declare an optional `carries` array of
load-direction strings describing which directions the joint transmits across the
seam, to support selecting a joint for an anisotropy-driven split. When the array is
absent the carried directions SHALL be treated as unspecified.

#### Scenario: Dovetail carries shear and locks pull-out
- **WHEN** the `dovetail_groove` entry is read
- **THEN** its `carries` SHALL include a shear direction and a lock direction

### Requirement: Inventory schema permits the taxonomy fields
`blocks/inventory_schema.json` SHALL allow optional `motion`, `reversible`, and
`carries` properties on inventory items, and SHALL include `hinge_axis`, `ball`,
`ball_socket`, `finger`, `mortise`, `tenon`, and `dowel` in the interface `type` enum.
Existing entries SHALL continue to validate without modification.

#### Scenario: Existing entries still validate after schema change
- **WHEN** the current `blocks/inventory.json` is validated against the updated schema
- **THEN** validation SHALL pass with no errors

#### Scenario: New taxonomy fields validate
- **WHEN** an entry with `motion: hinge`, `reversible: false`, and a non-empty
  `carries` array is validated
- **THEN** validation SHALL pass
