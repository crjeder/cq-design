## ADDED Requirements

### Requirement: Fin block builds a breakaway fin from explicit parameters
`blocks.breakaway_fin` SHALL return a single CadQuery solid consisting of a fin wall
standing off the part face by `standoff_mm` (default 0.2), horizontal tines one
`layer_height_mm` tall and `tine_width_mm` wide (default one nozzle width, bounded to
0.4-0.8 mm) that cross the standoff gap and overlap the part by at most `tine_overlap_mm`,
a rounded (never pointed) wall top, and an optional bed-pad ellipse 1 mm thick. It SHALL
take `anchor`, `down` (direction toward the bed), `height_mm` and `length_mm`, all in
build pose.

#### Scenario: Tines bridge the gap
- **WHEN** a fin is built with default parameters
- **THEN** every tine spans from the wall to at least the standoff plane plus
  `tine_overlap_mm` and its height equals `layer_height_mm`

#### Scenario: Rounded top
- **WHEN** a fin is built
- **THEN** the wall's top edges are filleted, so the sharp outer top corner is not part of the solid

#### Scenario: Tine count scales with height
- **WHEN** fins of height 10 mm and 40 mm are built
- **THEN** the 40 mm fin has at least as many tines as the 10 mm fin and at least 5 near
  its base

### Requirement: Fin block rejects invalid parameters with typed errors
The block SHALL raise a typed error rather than emit a degenerate fin when
`height_mm` or `length_mm` is not positive, `tine_width_mm` is outside 0.4-0.8 mm, or the
fin solid intersects the part body outside the tine overlap zone (`fin_collision`).

#### Scenario: Collision reported
- **WHEN** a fin is placed so its wall intersects the part body beyond the tine overlap
- **THEN** the block raises `fin_collision` naming the overlap volume

### Requirement: Placement script suggests fins from overhang regions
`src/fin_placement.py` SHALL read a print-pose STL and emit JSON with `success`,
`errors` and `fins`, each fin holding `anchor_xyz_mm`, `height_mm`, `length_mm` and
`region_area_mm2`, one per overhang region exceeding the plan overhang limit. It SHALL
reuse `mesh_io` overhang classification, skip regions reported as bridges, and SHALL NOT
modify any geometry or file other than its own output.

#### Scenario: Overhang gets a suggestion
- **WHEN** the STL has a 60 degree overhang region and `--overhang-deg 45`
- **THEN** `fins` contains one entry whose anchor lies on that region

#### Scenario: Self-supporting part
- **WHEN** no downward face exceeds the limit
- **THEN** `fins` is empty and `success` is true

#### Scenario: Bridge skipped
- **WHEN** an overhang region is a bridge under `bridge_max_mm`
- **THEN** no fin is suggested for it

### Requirement: Fins are a sacrificial union
A plan union entry MAY carry `sacrificial: true` (default false). Fin geometry SHALL be
emitted as its own union with that flag, never fused into the part body, and an existing
plan without the flag SHALL validate unchanged.

#### Scenario: Old plan validates
- **WHEN** a plan has no `sacrificial` key on any union
- **THEN** plan validation passes as before

### Requirement: Gate suggests fins as an opt-out hint
When the quality gate emits an `overhang_exceeded` warning for a union, it SHALL also emit
one `fin_hint` info finding carrying the `fin_placement` suggestions for that union, unless
`constraints.fin_hints` is `false` in `BUILD_PLAN.json` (default true). The hint SHALL never
change `passed`, SHALL never consume a fix round, and a failure computing it SHALL NOT fail
the gate.

#### Scenario: Hint emitted
- **WHEN** a union has a flagged overhang and `fin_hints` is absent
- **THEN** the report contains a `fin_hint` info finding with at least one fin

#### Scenario: Opt-out
- **WHEN** `constraints.fin_hints` is `false`
- **THEN** no `fin_hint` finding is emitted and `overhang_exceeded` is unchanged

#### Scenario: Plan schema accepts the flag
- **WHEN** a plan sets `constraints.fin_hints` to a boolean
- **THEN** plan validation passes; a non-boolean value fails validation
