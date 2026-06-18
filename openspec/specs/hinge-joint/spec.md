# Spec: hinge-joint

## Purpose

Parametric hinge joint block. Provides a `hinge_leaf` CadQuery workplane factory whose `A`/`B` leaves interleave their knuckles on a shared pin axis, with separate-pin and print-in-place variants.

## Requirements

### Requirement: Hinge leaf carries interleaving knuckles on a pin axis
The `hinge_leaf` function SHALL return a `cq.Workplane` of a flat leaf of width
`leaf_w` and thickness `leaf_t` joined to `knuckles` cylindrical knuckles of outer
diameter `d_outer` distributed along the hinge axis over `length`. Its signature SHALL
be `hinge_leaf(length, knuckles, d_outer, d_pin, leaf_w, leaf_t, clearance=0.3, side, variant)`.
The `side` argument SHALL select knuckle positions so that an `A` leaf and a `B` leaf
interleave without overlap given `clearance`.

#### Scenario: Opposite sides interleave
- **WHEN** an `A` leaf and a `B` leaf are generated with the same dimensions and `clearance=0.3`
- **THEN** their knuckles SHALL occupy disjoint axial bands with a gap of `clearance` between adjacent knuckles

### Requirement: Pin variant bores a pin hole; print-in-place leaves a gap
With `variant="pin"` the knuckles SHALL be bored with a coaxial hole of diameter
`d_pin` for a separate pin. With `variant="print_in_place"` the leaf pair SHALL be
generated with a radial and axial clearance gap so the knuckles print as one assembly
without fusing.

#### Scenario: Pin variant has a through bore
- **WHEN** `hinge_leaf(..., d_pin=3, variant="pin")` is generated
- **THEN** each knuckle SHALL contain a coaxial hole of diameter 3 mm

#### Scenario: Print-in-place variant has no separate pin hole sized for assembly
- **WHEN** `variant="print_in_place"` is generated
- **THEN** the knuckles SHALL be separated by the printable `clearance` gap rather than relying on an inserted pin

### Requirement: Hinge inventory entry states the required print orientation
The `hinge_leaf` inventory `use` string SHALL state the print axis required for the
knuckles to print without support and (for print-in-place) for the clearance gap to
resolve, because the joint is orientation-dependent.

#### Scenario: Use string names the print axis
- **WHEN** the `hinge_leaf` entry is read
- **THEN** its `use` string SHALL name the required print orientation
