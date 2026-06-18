## 1. Block Implementations

- [x] 1.1 Add `heat_set_boss(d_insert, h_insert, d_outer, h_boss)` to `src/blocks/fasteners.py` - cylinder boss with coaxial through-hole using `.circle().extrude().faces(">Z").hole()`
- [x] 1.2 Add `counterbore_hole(d_screw, d_head, h_head, depth)` to `src/blocks/fasteners.py` - union of wide shallow cylinder and narrow deep cylinder, both extruded from Z=0
- [x] 1.3 Add `countersink_hole(d_screw, angle, depth)` to `src/blocks/fasteners.py` - truncated cone frustum (`cq.Solid.makeCone`) unioned with shaft clearance cylinder; default `angle=90`
- [x] 1.4 Add `hex_nut_trap(nut_flat, nut_h, depth, d_screw=0)` to `src/blocks/fasteners.py` - hexagonal prism via `.polygon(6, nut_flat / math.cos(math.pi/6)).extrude(depth)`; subtract screw clearance cylinder when `d_screw > 0`
- [x] 1.5 Export all four new functions from `src/blocks/__init__.py` and add them to `__all__`

## 2. Inventory

- [x] 2.1 Add `heat_set_boss` descriptor to `src/blocks/inventory.json` with `use`, `params`, `dimensions=[7.5, 7.5, 8]` (typical M3), `interfaces: [{type: "screw_hole", ...}, {type: "face_mount", ...}]`
- [x] 2.2 Add `counterbore_hole` descriptor - `dimensions: null` (variable), `interfaces: [{type: "screw_hole", orientation: "+Z"}]`
- [x] 2.3 Add `countersink_hole` descriptor - `dimensions: null`, `interfaces: [{type: "screw_hole", orientation: "+Z"}]`
- [x] 2.4 Add `hex_nut_trap` descriptor - `dimensions: null`, `interfaces: [{type: "nut_trap", orientation: "+Z"}]`

## 3. Spec Update

- [x] 3.1 Update `openspec/specs/block-library/spec.md` - add `nut_trap` and `sliding_interface` to the interface type vocabulary in the "Interface type vocabulary is a closed set" requirement
- [x] 3.2 Update `openspec/specs/block-library/spec.md` - add the four new blocks to the "Initial inventory covers at least 10 common blocks" enumerated list

## 4. SKILL.md Reference Tables

- [x] 4.1 Add "Hardware Dimension Reference" section to `SKILL.md` with CNC Kitchen heat-set insert table (M2, M2.5, M3, M4: insert OD, insert length, recommended boss OD, recommended hole diameter for PLA)
- [x] 4.2 Add ISO 4762 SHCS table (M3, M4, M5: head diameter, head height, clearance hole diameter) to the reference section
- [x] 4.3 Add ISO 4032 hex nut table (M3, M4, M5: across flats, thickness) to the reference section

## 5. Tests

- [x] 5.1 Add `test_blocks.py` test cases for `heat_set_boss` - verify solid returns without error and bounding box dimensions match inputs
- [x] 5.2 Add test cases for `counterbore_hole` - verify bounding box height equals `depth`, top face pocket diameter ~= `d_head`
- [x] 5.3 Add test cases for `countersink_hole` - verify solid returns without error and can be subtracted from a slab to produce a valid STL
- [x] 5.4 Add test cases for `hex_nut_trap` - verify flat-to-flat dimension, verify screw clearance hole present when `d_screw > 0`
- [x] 5.5 Run `uv run pytest tests/test_blocks.py` - all new and existing tests pass
- [x] 5.6 Run `uv run pytest tests/test_plan_validate.py` - verify new blocks are accepted in `blocks_needed` fields
