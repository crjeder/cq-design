## ADDED Requirements

### Requirement: Tenon is a rectangular peg
`tenon(w, h, length, clearance=0.0)` SHALL return a `cq.Workplane` rectangular peg of
cross-section `w` by `h` extruded `length` along the mate axis, centered in X and Y,
with each cross-section dimension reduced by `2*clearance`.

#### Scenario: Tenon dimensions hold
- **WHEN** `tenon(w=8, h=4, length=10)` is generated
- **THEN** the bounding box SHALL be 8 x 4 mm in cross-section and 10 mm along the mate axis

### Requirement: Mortise is the matching pocket grown by clearance
`mortise(w, h, depth, clearance=0.2)` SHALL return a `cq.Workplane` rectangular pocket
solid of cross-section `w + 2*clearance` by `h + 2*clearance`, `depth` deep, intended to
be subtracted from a body.

#### Scenario: Mortise exceeds tenon by clearance
- **WHEN** `tenon(w=8, h=4, length=10)` and `mortise(w=8, h=4, depth=10, clearance=0.2)`
  are generated
- **THEN** the mortise cross-section SHALL exceed the tenon by `2*0.2` in both w and h

### Requirement: Rectangular section resists rotation
The tenon cross-section SHALL be rectangular (not circular) so the joint locks
rotation about the mate axis, distinguishing it from `alignment_pin`.

#### Scenario: Non-square section is keyed
- **WHEN** a tenon with `w != h` is generated
- **THEN** its cross-section SHALL be non-circular, preventing free rotation in the mortise
