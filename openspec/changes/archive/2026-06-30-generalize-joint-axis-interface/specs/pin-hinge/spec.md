## MODIFIED Requirements

### Requirement: Pin hinge is classified as a normal reversible revolute hinge
The `pin_hinge` inventory entry SHALL declare `motion: hinge`, `reversible: true`
(the filament strand can be withdrawn to separate the leaves), a single `joint_axis`
interface oriented `+Y`, and a `dof` describing its nominal revolute motion so it is
treated kinematically like any ordinary hinge rather than like the dof-less
`living-hinge` flexure. The `dof` SHALL be a revolute joint about the `Y` axis with a
`mechanical_limit` of `[0, 180]` degrees.

#### Scenario: Inventory taxonomy for the pin hinge
- **WHEN** the `pin_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge`, its `reversible` SHALL be `true`, it SHALL
  declare a `joint_axis` interface, and its `dof` SHALL be
  `{type: revolute, axis: Y, mechanical_limit: [0, 180], unit: deg}`
