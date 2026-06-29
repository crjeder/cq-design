## MODIFIED Requirements

### Requirement: Living hinge is classified as a permanent flexure hinge
The `living_hinge` inventory entry SHALL declare `motion: hinge`, `reversible: false`
(one continuous piece that cannot separate non-destructively), and a single
`joint_axis` interface oriented `+Y`.

#### Scenario: Inventory taxonomy for the living hinge
- **WHEN** the `living_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge`, its `reversible` SHALL be `false`, and it SHALL
  declare a `joint_axis` interface
