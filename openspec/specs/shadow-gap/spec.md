# Spec: shadow-gap

## Purpose

End-to-end seam edge detail. Provides a `shadow_gap` CadQuery workplane factory that
returns a return-lip for the front member so a butt joint shows a deliberate uniform
recessed reveal while the real, tolerance-driven seam is concealed behind the front wall.

## Requirements

### Requirement: Shadow gap returns an additive return-lip for the front member
The system SHALL provide a `shadow_gap` function in `blocks.joints` that returns a
`cq.Workplane` of a return-lip solid to `union` onto the inner face of the visible
(front) member's edge at an end-to-end seam. The lip SHALL be a bar of `length` (X) by
`overlap` (Y) by `wall` thickness (Z) projecting from the seam plane (Y=0) to
Y=`overlap`, so it stands behind the mating (back) member to conceal the real interface.
Its signature SHALL be `shadow_gap(length, wall, overlap=3.0)`. The deliberate reveal
and back-member setback are a placement relationship between two parts, documented in
the `use` string rather than encoded as geometry of this single additive lip.

#### Scenario: Lip projects behind the seam by the overlap
- **WHEN** `shadow_gap(length=50, wall=1.6, overlap=3.0)` is generated
- **THEN** the result SHALL be a single solid of length 50 mm (X) and thickness 1.6 mm
  (Z) extending from Y=0 to Y=3.0

### Requirement: Shadow gap documents the deliberate reveal and placement contract
The `shadow_gap` inventory `use` string SHALL state that the back member is placed
shortened by a deliberate reveal (~1 mm) and seated against the return lip with a small
clearance, so the only visible gap is the uniform recessed reveal while the real seam is
hidden behind the front member's return wall.

#### Scenario: Use string documents the reveal and back-member placement
- **WHEN** the `shadow_gap` inventory entry is read
- **THEN** its `use` string SHALL describe the deliberate reveal and the requirement to
  shorten the back member

### Requirement: Shadow gap is classified as a rigid separable seam
The `shadow_gap` inventory entry SHALL declare `motion: rigid`, `reversible: true`, and
a single `seam` interface oriented `+Y`.

#### Scenario: Inventory taxonomy for the shadow gap
- **WHEN** the `shadow_gap` entry is read
- **THEN** its `motion` SHALL be `rigid`, its `reversible` SHALL be `true`, and it SHALL
  declare a `seam` interface
