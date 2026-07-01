## RENAMED Requirements

- FROM: `### Requirement: Pin hinge returns both leaves as one print-in-place body`
- TO: `### Requirement: Pin hinge returns its two leaves as named member unions`

## MODIFIED Requirements

### Requirement: Pin hinge returns its two leaves as named member unions
The system SHALL provide a `pin_hinge` function in `blocks.joints` that returns a
`dict[str, cq.Workplane]` with exactly the keys `leaf_a` and `leaf_b` -- the two coplanar
flat leaves (each of width `leaf_w` and thickness `leaf_t`) whose `knuckles` cylindrical
knuckles interleave on a shared axis running along `+Y` over `length`, each bored by the
shared coaxial hole. Its signature SHALL be
`pin_hinge(length, knuckles, leaf_w, leaf_t, d_filament=1.9, clearance=0.25)`. The two
leaves SHALL be returned as separate, un-fused named bodies so a print-in-place hinge part
can declare them as two `unions` and the kinematic check can sweep one leaf against the
other. The `pin_hinge` inventory `use` string SHALL state that the block returns the two
leaves `leaf_a` and `leaf_b`.

#### Scenario: Two named leaves are returned as separate bodies
- **WHEN** `pin_hinge(length=30, knuckles=5, leaf_w=10, leaf_t=2)` is generated
- **THEN** the result SHALL be a dict `{"leaf_a": wp, "leaf_b": wp}` of two watertight
  bodies, each a flat leaf with its interleaved knuckles bored coaxially, whose knuckles
  occupy alternating axial bands separated by the `clearance` gap

#### Scenario: A print-in-place hinge part declares two unions
- **WHEN** a part whose script returns `pin_hinge(...)` declares
  `unions: [{"id": "leaf_a"}, {"id": "leaf_b"}]`
- **THEN** model export emits `leaf_a` and `leaf_b` as two separate unions, and the
  kinematic check can sweep `leaf_a` against `leaf_b`

### Requirement: Pin hinge is classified as a normal reversible revolute hinge
The `pin_hinge` inventory entry SHALL declare `motion: hinge`, `reversible: true`
(the filament strand can be withdrawn to separate the leaves), a single `joint_axis`
interface oriented `+Y`, and a `dof` describing its nominal revolute motion so it is
treated kinematically like any ordinary hinge rather than like the dof-less
`living-hinge` flexure. The `dof` SHALL be a revolute joint about `+Y` with a
`mechanical_limit` of `[0, 180]` degrees, expressed in the block-coordinate vector model
(`direction: [0, 1, 0]`, `origin: [0, 0, 0]`); the unit is derived from the type (`deg`)
and is not stored on the `dof`.

#### Scenario: Inventory taxonomy for the pin hinge
- **WHEN** the `pin_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge`, its `reversible` SHALL be `true`, it SHALL
  declare a `joint_axis` interface, and its `dof` SHALL be
  `{type: revolute, direction: [0, 1, 0], origin: [0, 0, 0], mechanical_limit: [0, 180]}`
