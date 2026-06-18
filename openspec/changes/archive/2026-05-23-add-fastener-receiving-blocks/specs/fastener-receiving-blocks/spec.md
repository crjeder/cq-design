## ADDED Requirements

### Requirement: heat_set_boss block
The system SHALL provide a `heat_set_boss(d_insert, h_insert, d_outer, h_boss)` function in `blocks/fasteners.py` that returns a `cq.Workplane` solid: a cylinder of diameter `d_outer` and height `h_boss` with a central through-hole of diameter `d_insert` and depth `h_insert`. The hole SHALL be coaxial with the outer cylinder. The caller passes the target hole diameter (insert OD minus press-fit tolerance) - the block does not apply any built-in tolerance offset.

#### Scenario: Basic heat_set_boss geometry
- **WHEN** `heat_set_boss(d_insert=4.4, h_insert=5.7, d_outer=7.5, h_boss=8.0)` is called
- **THEN** it returns a valid CadQuery Workplane with a solid that has outer diameter ~7.5 mm, height 8.0 mm, and a 4.4 mm diameter hole to depth 5.7 mm

#### Scenario: Boss integrates into a model via union
- **WHEN** a model script calls `body.union(heat_set_boss(4.4, 5.7, 7.5, 8.0))` on a CadQuery Workplane
- **THEN** the result exports to a valid, watertight STL with no geometry errors

---

### Requirement: counterbore_hole block
The system SHALL provide a `counterbore_hole(d_screw, d_head, h_head, depth)` function in `blocks/fasteners.py` that returns a `cq.Workplane` subtraction solid: a shallow cylinder of diameter `d_head` and height `h_head` (the counterbore pocket) joined with a deeper cylinder of diameter `d_screw` and height `depth` (the shaft clearance hole). Both cylinders SHALL be centered on the same axis. The caller subtracts this solid from their body to produce a counterbored hole.

#### Scenario: Basic counterbore_hole geometry
- **WHEN** `counterbore_hole(d_screw=3.4, d_head=5.5, h_head=3.0, depth=10.0)` is called
- **THEN** it returns a CadQuery Workplane solid whose bounding box height is `depth` and whose top face has a pocket of diameter ~5.5 mm to depth 3.0 mm

#### Scenario: Bolt head sits flush after cut
- **WHEN** a model script subtracts `counterbore_hole(3.4, 5.5, 3.0, 10.0)` from a 10 mm thick slab
- **THEN** the result exports to a valid, watertight STL with no geometry errors

---

### Requirement: countersink_hole block
The system SHALL provide a `countersink_hole(d_screw, angle, depth)` function in `blocks/fasteners.py` that returns a `cq.Workplane` subtraction solid: a tapered cone frustum (the countersink) joined with a cylinder of diameter `d_screw` and height `depth`. The taper angle SHALL be the included half-angle computed as `(180 - angle) / 2` degrees from vertical, producing an opening of `d_screw + 2 * depth_of_sink * tan(half_angle)` at the top face. The default `angle` SHALL be 90 degrees (DIN 7991 standard).

#### Scenario: Basic countersink_hole geometry
- **WHEN** `countersink_hole(d_screw=3.0, angle=90, depth=8.0)` is called
- **THEN** it returns a CadQuery Workplane solid that can be subtracted from a slab to produce a 90-degree conical countersink

#### Scenario: Flat head screw sits flush after cut
- **WHEN** a model script subtracts `countersink_hole(3.0, 90, 10.0)` from a 10 mm thick slab
- **THEN** the result exports to a valid, watertight STL with no geometry errors

---

### Requirement: hex_nut_trap block
The system SHALL provide a `hex_nut_trap(nut_flat, nut_h, depth, d_screw=0)` function in `blocks/fasteners.py` that returns a `cq.Workplane` subtraction solid: a regular hexagonal prism with flat-to-flat distance `nut_flat` and height `depth`. When `d_screw > 0`, a cylindrical through-hole of diameter `d_screw` and height `depth` SHALL be coaxially subtracted from the hex prism, leaving an open bottom for the screw to pass through.

#### Scenario: Hex nut trap without screw clearance
- **WHEN** `hex_nut_trap(nut_flat=5.5, nut_h=2.4, depth=3.0)` is called
- **THEN** it returns a hexagonal prism solid where the flat-to-flat distance is ~5.5 mm and height is 3.0 mm

#### Scenario: Hex nut trap with screw clearance hole
- **WHEN** `hex_nut_trap(nut_flat=5.5, nut_h=2.4, depth=8.0, d_screw=3.2)` is called
- **THEN** it returns a solid with the hex pocket and a 3.2 mm diameter cylinder through the full depth

#### Scenario: Captured nut after cut
- **WHEN** a model script subtracts `hex_nut_trap(5.5, 2.4, 3.0)` from a 10 mm wall body
- **THEN** the result exports to a valid, watertight STL with no geometry errors

---

### Requirement: New blocks registered in inventory
The system SHALL include entries for `heat_set_boss`, `counterbore_hole`, `countersink_hole`, and `hex_nut_trap` in `blocks/inventory.json`, each with `name`, `module`, `function`, `use`, `params`, `dimensions`, and `interfaces` fields conforming to the block-library schema.

#### Scenario: Plan references heat_set_boss
- **WHEN** `BUILD_PLAN.json` lists `heat_set_boss` in a part's `blocks_needed`
- **THEN** `plan_validate.py` passes without error

#### Scenario: Plan references hex_nut_trap
- **WHEN** `BUILD_PLAN.json` lists `hex_nut_trap` in a part's `blocks_needed`
- **THEN** `plan_validate.py` passes without error

---

### Requirement: SKILL.md hardware dimension reference tables
`SKILL.md` SHALL include a reference table section with standard dimensions for: CNC Kitchen heat-set inserts (M2, M2.5, M3, M4 - insert OD, insert length, recommended boss OD, recommended hole diameter for PLA), ISO 4762 SHCS (M3, M4, M5 - head diameter, head height, clearance hole diameter), and ISO 4032 hex nuts (M3, M4, M5 - across flats, thickness).

#### Scenario: Planning LLM uses correct M3 heat-set dimensions
- **WHEN** a developer reads SKILL.md
- **THEN** they find the M3 CNC Kitchen insert OD (4.6 mm), insert length (5.7 mm), recommended boss OD (7.5 mm), and recommended hole diameter for PLA (4.4 mm)
