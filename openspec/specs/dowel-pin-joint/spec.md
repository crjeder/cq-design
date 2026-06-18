# Spec: dowel-pin-joint

## Purpose

Parametric dowel-pin joint blocks. Provides matched `dowel_pin` (chamfered cylinder) and `dowel_bore` (cylindrical pocket) CadQuery workplane factories whose fit is set by the sign of the clearance.

## Requirements

### Requirement: Dowel pin is a chamfered cylinder
`dowel_pin(d, length, chamfer=0.4)` SHALL return a `cq.Workplane` cylinder of diameter
`d` and height `length` with a lead-in chamfer at the inserting end.

#### Scenario: Dowel dimensions hold
- **WHEN** `dowel_pin(d=4, length=12)` is generated
- **THEN** the bounding box SHALL be 4 mm in diameter and 12 mm tall, centered on the axis

### Requirement: Dowel bore fit is set by clearance sign
`dowel_bore(d, depth, clearance=0.1)` SHALL return a `cq.Workplane` bore solid of
diameter `d + 2*clearance` and `depth` deep, intended to be subtracted. A positive
`clearance` SHALL yield a slip (separable) fit; a negative `clearance` SHALL yield an
interference (press, permanent) fit.

#### Scenario: Positive clearance is a slip fit
- **WHEN** `dowel_pin(d=4, length=12)` and `dowel_bore(d=4, depth=12, clearance=0.1)`
  are generated
- **THEN** the bore diameter SHALL exceed the pin diameter by `2*0.1`

#### Scenario: Negative clearance is interference
- **WHEN** `dowel_bore(d=4, depth=12, clearance=-0.1)` is generated
- **THEN** the bore diameter SHALL be smaller than the nominal pin by `2*0.1`, producing a press fit
