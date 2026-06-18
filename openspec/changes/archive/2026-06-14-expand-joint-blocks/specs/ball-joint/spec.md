## ADDED Requirements

### Requirement: Ball stud is a sphere on a printable stem
`ball_stud(d_ball, d_stem, stem_l, fillet)` SHALL return a `cq.Workplane` of a sphere of
diameter `d_ball` joined to a coaxial stem of diameter `d_stem` and length `stem_l`,
with a fillet blending the stem into the underside of the ball for support-free
printing in the stated orientation.

#### Scenario: Ball and stem dimensions hold
- **WHEN** `ball_stud(d_ball=10, d_stem=5, stem_l=8, fillet=2)` is generated
- **THEN** the maximum cross-section diameter SHALL equal `d_ball` (10 mm)
- **AND** the overall height SHALL be at least `stem_l + d_ball`

### Requirement: Ball socket is a slotted snap-in cup that retains past the equator
`ball_socket(d_ball, retention_angle, slot_w, wall, clearance=0.2)` SHALL return a
`cq.Workplane` cup whose internal cavity is a sphere of `d_ball + 2*clearance`, whose
mouth opening diameter is smaller than `d_ball` (so the ball is captured past its
equator), and which contains a slot of width `slot_w` letting the cup flex during
snap-in.

#### Scenario: Mouth retains the ball
- **WHEN** `ball_socket(d_ball=10, retention_angle=30, slot_w=2, wall=2)` is generated
- **THEN** the mouth opening diameter SHALL be less than 10 mm

#### Scenario: Cavity exceeds the ball by clearance for free movement
- **WHEN** the socket is generated with `clearance=0.2`
- **THEN** the internal spherical cavity diameter SHALL equal `d_ball + 2*0.2`

#### Scenario: Slot is present for flex
- **WHEN** a ball socket is generated
- **THEN** the solid SHALL contain a slot of width `slot_w` breaking the cup rim
