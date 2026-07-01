## MODIFIED Requirements

### Requirement: Joints are classified by motion and reversibility
Every joint inventory entry SHALL be classifiable along two orthogonal axes:
`motion` (the relative movement permitted after assembly) and `reversible` (whether
the joint can be separated non-destructively). `motion` SHALL be one of `rigid`,
`hinge`, or `ball`. `reversible` SHALL be a boolean recording the joint's default fit.

#### Scenario: Pin hinge is mobile and reversible
- **WHEN** the `pin_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge` and its `reversible` SHALL be `true`

#### Scenario: Sliding dovetail is rigid and separable
- **WHEN** the `dovetail_tongue` entry is read
- **THEN** its `motion` SHALL be `rigid` and its `reversible` SHALL be `true`

#### Scenario: Press-fit dowel is rigid and permanent
- **WHEN** the `dowel_bore` entry is read with its default (interference) clearance
- **THEN** its `motion` SHALL be `rigid` and its `reversible` SHALL be `false`
