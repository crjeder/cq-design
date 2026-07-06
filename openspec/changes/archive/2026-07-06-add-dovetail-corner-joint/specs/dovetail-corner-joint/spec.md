## ADDED Requirements

### Requirement: Dovetail corner joint is a matched-pair block returning pins and tails
`dovetail_corner_joint(pin_count, pin_width, tail_width, board_thickness, tooth_length, flare_deg=15.0, corner_angle_deg=90.0, clearance=0.1)` SHALL return a `dict[str, cq.Workplane]` with exactly two keys, `"pins"` and `"tails"`, both derived from one shared per-tooth trapezoid comb so the two stay geometrically complementary. `"pins"` SHALL be a positive comb of `pin_count` teeth for the caller to `.union()` onto the pin board's end face. `"tails"` SHALL be a socket-shaped cutting tool for the caller to `.cut()` from the tail board's end face.

#### Scenario: Returns exactly two named members
- **WHEN** `dovetail_corner_joint` is called with any valid parameters
- **THEN** the returned dict SHALL have exactly the keys `"pins"` and `"tails"`, each a `cq.Workplane`

#### Scenario: Pins comb spans the tiled tooth count
- **WHEN** `dovetail_corner_joint(pin_count=4, pin_width=1, tail_width=1, board_thickness=0.75, tooth_length=0.75)` is called
- **THEN** the `"pins"` bounding box X-span SHALL equal `pin_count * pin_width + (pin_count - 1) * tail_width` (7 mm)

#### Scenario: Comb is centered in X
- **WHEN** `dovetail_corner_joint` is called with any `pin_count`, `pin_width`, `tail_width`
- **THEN** both the `"pins"` and `"tails"` bounding boxes SHALL be symmetric about X=0

### Requirement: Flare angle is a distinct parameter from the sliding dovetail's angle convention
`flare_deg` SHALL control the per-tooth taper measured from the tooth's straight side (0 = rectangular finger-joint tooth, larger = more dovetail undercut), computed as `half_top = half_base - tan(radians(flare_deg)) * board_thickness` reusing the same trapezoid-profile shape as `dovetail_groove`/`dovetail_tongue`. This convention SHALL NOT be conflated with `dovetail_groove`/`dovetail_tongue`'s `angle` parameter (measured from vertical, opposite sense); the two SHALL remain independently named parameters.

#### Scenario: Zero flare produces a rectangular tooth
- **WHEN** `dovetail_corner_joint` is called with `flare_deg=0`
- **THEN** each tooth's top width SHALL equal its base width (`pin_width`), producing a straight-sided (finger-joint-shaped) tooth

#### Scenario: Default flare matches the reference convention
- **WHEN** `dovetail_corner_joint` is called with default `flare_deg=15.0`
- **THEN** each tooth's top width SHALL equal `pin_width - 2 * tan(radians(15)) * board_thickness`

### Requirement: Corner angle generalizes the fixed 90-degree assumption
`corner_angle_deg` SHALL control the dihedral angle, about the shared tooth-tiling (X) edge, between the `"pins"` member's natural frame and the `"tails"` member's frame, replacing a hardcoded 90-degree rotation. At `corner_angle_deg=90` (the default), the relative transform between `"pins"` and `"tails"` SHALL match the perpendicular-corner case. This parameter SHALL only affect the tooth/socket feature geometry; it SHALL NOT generate or miter any surrounding board body.

#### Scenario: Default corner angle matches a perpendicular corner
- **WHEN** `dovetail_corner_joint` is called with default `corner_angle_deg=90.0`
- **THEN** the `"tails"` member SHALL be rotated 90 degrees about the X axis relative to the `"pins"` member's natural frame

#### Scenario: Non-default corner angle rotates the tails member accordingly
- **WHEN** `dovetail_corner_joint` is called with `corner_angle_deg=60.0`
- **THEN** the `"tails"` member SHALL be rotated 60 degrees about the X axis relative to the `"pins"` member's natural frame, not 90

### Requirement: Clearance is a real per-side mating gap, applied to the tails cutting tool
`clearance` SHALL grow the `"tails"` socket profile (both `half_top` and `half_base`) by `clearance` per side relative to the `"pins"` comb's nominal dimensions, leaving `"pins"` unchanged. Positive `clearance` (default 0.1) SHALL yield a separable gap fit; negative `clearance` SHALL yield an interference (press) fit, following the joint-classification sign convention.

#### Scenario: Positive clearance grows the tail socket
- **WHEN** `dovetail_corner_joint` is called with `clearance=0.1`
- **THEN** the `"tails"` socket cross-section SHALL be `0.2` mm wider (both `half_top` and `half_base` grown by `0.1` each) than the `"pins"` comb's nominal tooth cross-section at the same Z

#### Scenario: Negative clearance shrinks the tail socket for an interference fit
- **WHEN** `dovetail_corner_joint` is called with `clearance=-0.1`
- **THEN** the `"tails"` socket cross-section SHALL be narrower than the `"pins"` comb's nominal tooth cross-section, producing interference when assembled

#### Scenario: Zero clearance reproduces the reference's theoretical exact fit
- **WHEN** `dovetail_corner_joint` is called with `clearance=0`
- **THEN** the `"tails"` socket cross-section SHALL exactly match the `"pins"` comb's nominal tooth cross-section

### Requirement: Inventory declares the matched-pair mating contract
`blocks/inventory.json` SHALL contain a `dovetail_corner_joint` entry with `emits: ["pins", "tails"]`, `motion: "rigid"`, `reversible: true`, a `carries` array including a shear direction, and one interface of the new `dovetail_corner` type on each conceptual member. The entry's `use` text SHALL document, in prose, which dict key each board pulls and that a `joints` entry (not the same-part `unions` array) is the expected way to wire two different boards, mirroring the self-documenting convention already established by the `pin_hinge` entry.

#### Scenario: Entry declares emits for the matched pair
- **WHEN** `blocks/inventory.json` is validated
- **THEN** the `dovetail_corner_joint` entry SHALL pass schema validation with `emits: ["pins", "tails"]`

#### Scenario: Entry can back a joints entry
- **WHEN** a `BUILD_PLAN.json` `joints` entry names `block: "dovetail_corner_joint"` with `members: [{member: "pins", part: ...}, {member: "tails", part: ...}]`
- **THEN** `plan_validate.py` SHALL accept it as a valid matched-pair reference (no "no emits descriptor" or "unknown emits id" error)

#### Scenario: Use text documents the mating contract
- **WHEN** the `dovetail_corner_joint` inventory entry's `use` field is read
- **THEN** it SHALL explain that the `"pins"` member is unioned onto the pin board and the `"tails"` member is cut from the tail board, and that the two boards are ordinarily separate parts wired via a `joints` entry
