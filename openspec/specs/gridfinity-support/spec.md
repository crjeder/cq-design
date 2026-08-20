# Gridfinity Support

## Purpose

Defines requirements for building parts that conform to the Gridfinity modular storage standard: the `blocks/gridfinity.py` block family, the Gridfinity archetype templates, the `reference/gridfinity.md` dimension reference, and the `gridfinity_check.py` conformance stage. Gridfinity's value is interoperability with parts printed by other people, so its dimensions are a fixed external standard, not design choices — the requirements below exist so a Gridfinity request never routes through a hand-modelled approximation of the profile.

## Requirements

### Requirement: Gridfinity dimensions come from the standard, never from research or invention

The system SHALL carry the published Gridfinity dimensions in `reference/gridfinity.md` and as module constants in `blocks/gridfinity.py`: 42 mm grid pitch, 7 mm height unit, 0.5 mm inter-bin gap, the 0.8 / 1.8 / 2.15 mm foot profile with a 3.75 mm top corner radius, the 0.7 / 1.8 / 1.9 mm stacking-lip recess, and 6.5 x 2.4 mm magnet pockets with 3.0 mm screw holes on a 26 mm spacing.

Phase 1 SHALL NOT spawn a dimension-research lookup for these values, and Phase 3 SHALL read `reference/gridfinity.md` before authoring any part that uses a Gridfinity block.

#### Scenario: Gridfinity request skips dimension research
- **WHEN** a request names Gridfinity and needs no other real-world object measured
- **THEN** no research agent is spawned for the grid, profile, or hole dimensions, and the values are taken from `reference/gridfinity.md`

#### Scenario: Object to be held is still researched
- **WHEN** a Gridfinity request names a real object the bin must hold
- **THEN** that object's dimensions are looked up as usual and drive the unit count

### Requirement: Gridfinity block family covers bins, baseplates, and grid-compatibility of arbitrary parts

The system SHALL provide, in `blocks/gridfinity.py` and exported from `blocks`:

- `gridfinity_bin(cols, rows, height_u, ...)` — a complete bin (feet, walls, cavity, stacking lip) with optional dividers, label shelf, finger scoop, magnet/screw pockets, and a `solid=True` blank mode for custom pockets
- `gridfinity_baseplate(cols, rows, ...)` — a complete baseplate of sockets
- `gridfinity_feet(cols, rows, ...)` — the foot array alone, for unioning under an arbitrary body
- `gridfinity_socket_cutter(cols, rows, ...)` — the socket array alone, for cutting into an arbitrary plate
- `gridfinity_dimensions(...)` and `gridfinity_units_for(...)` — the numbers without geometry

Every returned solid SHALL sit with its print-bed face at Z = 0 and its footprint centered on the origin, matching the rest of the block library. Each block SHALL appear in `blocks/inventory.json` with its params and interfaces.

#### Scenario: Bin outer dimensions follow the grid
- **WHEN** `gridfinity_bin(cols, rows, height_u)` is called
- **THEN** the solid measures `42 * cols - 0.5` by `42 * rows - 0.5` mm with its body top at `7 * height_u` mm and its underside at Z = 0

#### Scenario: Baseplates tile edge to edge
- **WHEN** `gridfinity_baseplate(cols, rows)` is called
- **THEN** the plate spans the full `42 * cols` by `42 * rows` mm, so two plates placed side by side keep the grid pitch across the seam

#### Scenario: An arbitrary part is made grid-compatible
- **WHEN** `gridfinity_feet(cols, rows)` is unioned under a custom body that starts at Z = 4.75 and spans no more than the bin footprint
- **THEN** the combined part drops into a standard baseplate

#### Scenario: Parameters that cannot produce a valid part are rejected
- **WHEN** a call asks for geometry the standard cannot express (zero grid units, a bin with no room for a cavity, a baseplate thinner than the socket profile, magnet pockets with no stock under them)
- **THEN** the block raises `ValueError` naming the offending parameter rather than returning malformed geometry

### Requirement: Bins and baseplates mate with independently built standard parts

Geometry produced by the Gridfinity blocks SHALL interoperate with parts built to the published standard: a bin's feet SHALL seat in a baseplate socket, and a bin's stacking lip SHALL accept the feet of a bin placed on top, in both cases without material interference at the seated position.

The stacking lip's rim SHALL be printable — the standard's sharp rim profile ends in a knife edge below one extrusion width, so the rounded rim profile is the default; blunting it lowers the lip apex by `sqrt(2)` times the fillet radius, and `gridfinity_dimensions` SHALL report that as-built height.

#### Scenario: A bin drops into a baseplate
- **WHEN** a bin is placed at its seated position over any cell of a baseplate of matching pitch
- **THEN** the intersection volume of the two solids is zero within boolean tolerance

#### Scenario: Bins stack on the height module
- **WHEN** a bin is placed on top of another bin's stacking lip at its seated position
- **THEN** the intersection volume is zero within boolean tolerance and the stack grows by `7 * height_u` per bin

#### Scenario: An off-grid part is still retained
- **WHEN** a foot array is offset 2 mm from a socket's center
- **THEN** the solids interfere, confirming the socket registers the part laterally rather than accepting anything

### Requirement: Gridfinity conformance is checked deterministically, not visually

The system SHALL provide `src/gridfinity_check.py`, which re-runs a part script and reports findings in the shared quality-gate issue contract plus a `detected` block naming how the part was read (kind, grid size, height units, lip). It SHALL check, as blocking errors: the underside resting on the bed (`gridfinity_bed_offset`), the footprint on the 42 mm grid (`gridfinity_footprint`), the body height on the 7 mm module (`gridfinity_height`), the foot profile's width at three heights and one foot pad per cell (`gridfinity_base_profile`), and interference-free mating against reference standard geometry (`gridfinity_mate`).

The check SHALL run as a quality-gate stage scoped automatically to part scripts that use a Gridfinity block, and SHALL degrade to a `check_skipped` warning — never a false failure — when the script cannot be loaded.

#### Scenario: A standard bin passes
- **WHEN** the check runs on a part built with `gridfinity_bin`
- **THEN** it reports no issues and exits 0

#### Scenario: A hand-modelled bin is rejected with the failing dimension named
- **WHEN** the check runs on a plain rounded box on a 42 mm footprint with no foot profile
- **THEN** it reports `gridfinity_footprint`, `gridfinity_base_profile`, and `gridfinity_mate` errors naming the measured and expected values, and exits 1

#### Scenario: Non-Gridfinity parts are unaffected
- **WHEN** the quality gate runs on a part script that uses no Gridfinity block
- **THEN** the Gridfinity stage contributes no issues and does no geometry work

#### Scenario: Interior features are not mistaken for a broken lip
- **WHEN** a bin carries dividers or a label shelf reaching the wall top
- **THEN** the stacking check considers only material above the body top, so those features are not reported as stacking interference

### Requirement: Gridfinity requests route through archetypes

The system SHALL provide `gridfinity-bin` and `gridfinity-baseplate` archetype templates in `templates/`, indexed in `templates/archetypes.json` with Gridfinity aliases, so the Phase 3 archetype match resolves a Gridfinity request to a pre-verified template rather than scratch geometry.

#### Scenario: Archetype match on a Gridfinity request
- **WHEN** a part's request or plan names Gridfinity
- **THEN** the Phase 3 archetype step matches `gridfinity-bin` (or `gridfinity-baseplate` for the grid itself) and starts from that template
