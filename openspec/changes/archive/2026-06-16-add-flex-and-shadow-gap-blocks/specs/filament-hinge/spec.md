## ADDED Requirements

### Requirement: Filament hinge returns both leaves as one print-in-place body
The system SHALL provide a `filament_hinge` function in `blocks.joints` that returns a
single `cq.Workplane` containing two coplanar flat leaves (each of width `leaf_w` and
thickness `leaf_t`) whose `knuckles` cylindrical knuckles interleave on a shared axis
running along `+Y` over `length`. Its signature SHALL be
`filament_hinge(length, knuckles, leaf_w, leaf_t, d_filament=1.9, clearance=0.25)`.
Unlike `hinge_leaf`, which returns one leaf, `filament_hinge` SHALL return the complete
two-leaf hinge as one body suitable for printing in place.

#### Scenario: Single body contains both leaves and interleaved knuckles
- **WHEN** `filament_hinge(length=30, knuckles=5, leaf_w=10, leaf_t=2)` is generated
- **THEN** the result SHALL be one `cq.Workplane` whose knuckles occupy alternating
  axial bands separated by the `clearance` gap, with a flat leaf on each side of the axis

### Requirement: Knuckles are bored coaxially for a filament pin
The knuckles SHALL be bored with one coaxial through-hole of diameter `d_filament` so a
snipped strand of 1.75 mm filament can serve as the pivot pin. The default `d_filament`
of 1.9 mm SHALL provide a slip fit over 1.75 mm filament to compensate for FDM holes
printing undersized.

#### Scenario: Coaxial bore sized for filament
- **WHEN** `filament_hinge(..., d_filament=1.9)` is generated
- **THEN** the knuckles SHALL share one coaxial hole of diameter 1.9 mm

### Requirement: Print-in-place clearance prevents knuckle fusing
The axial `clearance` between adjacent knuckles SHALL be a parameter whose value must
exceed one layer height so the interleaved knuckles print as one assembly without
fusing. The inventory `use` string SHALL state the required print orientation (knuckle
axis in the build plane) for the bore to bridge cleanly and the undersides to
self-support.

#### Scenario: Use string names the print orientation
- **WHEN** the `filament_hinge` inventory entry is read
- **THEN** its `use` string SHALL name the required flat print orientation with the
  knuckle axis in the build plane

### Requirement: Filament hinge is classified as a reversible hinge
The `filament_hinge` inventory entry SHALL declare `motion: hinge`, `reversible: true`
(the filament strand can be withdrawn to separate the leaves), and a single
`hinge_axis` interface oriented `+Y`.

#### Scenario: Inventory taxonomy for the filament hinge
- **WHEN** the `filament_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge`, its `reversible` SHALL be `true`, and it SHALL
  declare a `hinge_axis` interface
