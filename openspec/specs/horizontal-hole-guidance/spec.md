# Horizontal Hole Guidance

## Purpose

Steers builders to `teardrop_bore` / `teardrop_post` for horizontal holes and pegs via a prompt rule, an advisory lint, and a gate hint, with the peak facing print-up.

## Requirements

### Requirement: Builder prompt routes horizontal holes to teardrop blocks
The part-builder prompt SHALL instruct the builder to use `teardrop_bore` for round holes whose axis lies in the build plane at the chosen print pose, and `teardrop_post` for free horizontal pegs of diameter >= 3 mm, and a plain bore for vertical holes.

#### Scenario: Rule present in rendered prompt
- **WHEN** a part prompt is rendered
- **THEN** it contains the horizontal-hole rule naming `teardrop_bore` and `teardrop_post`

### Requirement: Lint flags hand-rolled horizontal round holes
`script_lint` SHALL emit an advisory (non-blocking) finding when a part script cuts a circular hole on a side-facing workplane and the script does not use `teardrop_bore`.

#### Scenario: Round hole on a side workplane
- **WHEN** a script calls `.faces(">Y").workplane().hole(d)` and never references `teardrop_bore`
- **THEN** lint reports an advisory finding naming `teardrop_bore`

#### Scenario: Teardrop block used
- **WHEN** the same script also calls `teardrop_bore`
- **THEN** no such finding is emitted

#### Scenario: Vertical hole
- **WHEN** the hole is cut on a `>Z` or `<Z` face
- **THEN** no finding is emitted

### Requirement: Overhang hint names the teardrop block
When the quality gate emits an `overhang_exceeded` warning, its hint SHALL mention `teardrop_bore` for horizontal holes in addition to chamfers/redesign.

#### Scenario: Overhang warning
- **WHEN** the gate emits a non-advisory `overhang_exceeded` warning
- **THEN** the hint text contains `teardrop_bore`

### Requirement: teardrop_bore peak direction is selectable
`teardrop_bore` SHALL accept `peak` of `"up"` (default, +Z) or `"down"` (-Z) so the roof peak can face print-up when the part prints flipped.

#### Scenario: Flipped print pose
- **WHEN** `teardrop_bore(d, depth, peak="down")` is built
- **THEN** its apex lies at -Z and the arc portion at +Z

#### Scenario: Default unchanged
- **WHEN** `peak` is omitted
- **THEN** the geometry equals the current +Z-peak cutter
