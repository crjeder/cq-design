## Why

The blocks library covers self-tapping screws and PCB standoffs but has no receiving-feature blocks for the three other common FDM fastener systems: heat-set inserts, socket head cap screws with counterbores, flat-head countersinks, and captured hex nuts. Model scripts that need these must hand-code the geometry from scratch, which leads to incorrect dimensions and inconsistent results.

## What Changes

- Add `heat_set_boss` to `blocks/fasteners.py` - a printable boss sized for hot-press brass heat-set inserts (M2-M4 standard dimensions)
- Add `counterbore_hole` to `blocks/fasteners.py` - a counterbore + clearance hole subtraction for socket head cap screws (ISO 4762)
- Add `countersink_hole` to `blocks/fasteners.py` - a tapered countersink subtraction for flat-head screws (DIN 7991, 90 deg standard angle)
- Add `hex_nut_trap` to `blocks/fasteners.py` - a hexagonal pocket subtraction for top-drop captured nuts, with optional screw clearance hole
- Add all four blocks to `blocks/inventory.json` with full descriptors (use, params, dimensions, interfaces)
- Add interface type `nut_trap` to the closed vocabulary in `block-library` spec (hex nut pocket is distinct from `socket` or `screw_hole`)
- Add standard dimension reference tables (CNC Kitchen inserts, ISO 4762 SHCS, ISO 4032 hex nuts) to `SKILL.md` so the LLM can look up correct dimensions during planning

## Capabilities

### New Capabilities
- `fastener-receiving-blocks`: Four parametric blocks covering the primary threaded fastener systems used in FDM enclosure design (heat-set inserts, SHCS counterbores, flat-head countersinks, captured hex nuts)

### Modified Capabilities
- `block-library`: Interface type vocabulary must be extended with `nut_trap` to cover the hex nut pocket interface; also adds `sliding_interface` which was introduced by the dovetail change but never added to the spec's closed vocabulary

## Impact

- `src/blocks/fasteners.py`: 4 new functions (~15 lines each)
- `src/blocks/inventory.json`: 4 new block descriptors
- `openspec/specs/block-library/spec.md`: interface vocabulary update
- `SKILL.md`: new reference tables section
- No changes to `orchestrate.py`, `run_cadquery_model.py`, or any pipeline scripts
- No new dependencies
