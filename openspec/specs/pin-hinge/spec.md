# Spec: pin-hinge

## Purpose

Compact print-in-place MECHANICAL hinge piloted by a 1.75 mm filament strand: rigid
leaves rotate about a separate pin threaded through interleaved knuckles. Functionally
it is a NORMAL revolute hinge (one rotational DOF, like a door hinge); the pin merely
happens to be a snipped strand of filament. This is distinct from the `living-hinge`
flexure (which has no pin and bends a thin web). Provides a `pin_hinge` CadQuery
workplane factory that returns both interleaved leaves as one flat body whose coaxial
knuckle bore takes a snipped length of filament as the pivot pin.

## Requirements

### Requirement: Pin hinge returns both leaves as one print-in-place body
The system SHALL provide a `pin_hinge` function in `blocks.joints` that returns a
single `cq.Workplane` containing two coplanar flat leaves (each of width `leaf_w` and
thickness `leaf_t`) whose `knuckles` cylindrical knuckles interleave on a shared axis
running along `+Y` over `length`. Its signature SHALL be
`pin_hinge(length, knuckles, leaf_w, leaf_t, d_filament=1.9, clearance=0.25)`.
Unlike `hinge_leaf`, which returns one leaf, `pin_hinge` SHALL return the complete
two-leaf hinge as one body suitable for printing in place.

#### Scenario: Single body contains both leaves and interleaved knuckles
- **WHEN** `pin_hinge(length=30, knuckles=5, leaf_w=10, leaf_t=2)` is generated
- **THEN** the result SHALL be one `cq.Workplane` whose knuckles occupy alternating
  axial bands separated by the `clearance` gap, with a flat leaf on each side of the axis

### Requirement: Knuckles are bored coaxially for a filament pin
The knuckles SHALL be bored with one coaxial through-hole of diameter `d_filament` so a
snipped strand of 1.75 mm filament can serve as the pivot pin. The default `d_filament`
of 1.9 mm SHALL provide a slip fit over 1.75 mm filament to compensate for FDM holes
printing undersized.

#### Scenario: Coaxial bore sized for filament
- **WHEN** `pin_hinge(..., d_filament=1.9)` is generated
- **THEN** the knuckles SHALL share one coaxial hole of diameter 1.9 mm

### Requirement: Print-in-place clearance prevents knuckle fusing
The axial `clearance` between adjacent knuckles SHALL be a parameter whose value must
exceed one layer height so the interleaved knuckles print as one assembly without
fusing. The inventory `use` string SHALL state the required print orientation (knuckle
axis in the build plane) for the bore to bridge cleanly and the undersides to
self-support.

#### Scenario: Use string names the print orientation
- **WHEN** the `pin_hinge` inventory entry is read
- **THEN** its `use` string SHALL name the required flat print orientation with the
  knuckle axis in the build plane

### Requirement: Pin hinge is classified as a normal reversible revolute hinge
The `pin_hinge` inventory entry SHALL declare `motion: hinge`, `reversible: true`
(the filament strand can be withdrawn to separate the leaves), a single `hinge_axis`
interface oriented `+Y`, and a `dof` describing its nominal revolute motion so it is
treated kinematically like any ordinary hinge rather than like the dof-less
`living-hinge` flexure. The `dof` SHALL be a revolute joint about the `Y` axis with a
`mechanical_limit` of `[0, 180]` degrees.

#### Scenario: Inventory taxonomy for the pin hinge
- **WHEN** the `pin_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge`, its `reversible` SHALL be `true`, it SHALL
  declare a `hinge_axis` interface, and its `dof` SHALL be
  `{type: revolute, axis: Y, mechanical_limit: [0, 180], unit: deg}`
