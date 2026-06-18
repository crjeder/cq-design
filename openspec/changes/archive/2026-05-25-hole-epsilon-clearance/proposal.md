## Why

When a subtractive solid (hole, cutout, slot) is exactly as deep as the material it cuts through, the BREP kernel leaves a coincident face at the exit surface. This causes z-fighting in preview renders and can produce degenerate topology that breaks watertightness checks. Adding a tiny epsilon overcut guarantees a clean boolean difference every time.

## What Changes

- All block functions that return subtractive solids will extrude by `depth + _EPS` instead of `depth`, where `_EPS` is a module-level constant set to the smallest representable positive float that OCC can meaningfully distinguish (recommended starting value: `1e-4` mm, which is below FDM resolution and above OCC's internal tolerance of ~`1e-7`).
- Affected functions in `src/blocks/fasteners.py`: `counterbore_hole`, `countersink_hole`, `hex_nut_trap`, `alignment_socket`, `snap_socket_receiver`.
- Affected functions in `src/blocks/connectors.py`: `port_cutout`, `cable_slot`, `vent_grid`.
- The epsilon is applied only to the extrusion axis that exits the material face; lateral dimensions are unchanged.
- `_EPS` is defined once per module (not per-function) and is not exposed as a parameter -- callers do not need to know about it.

## Capabilities

### New Capabilities

*(none)*

### Modified Capabilities

- `block-library`: All subtractive blocks must overcut the material depth by a fixed epsilon to prevent coincident-face artifacts in boolean operations.

## Impact

- `src/blocks/fasteners.py` -- five functions modified.
- `src/blocks/connectors.py` -- three functions modified.
- `src/blocks/inventory.json` -- no changes needed; the epsilon is an implementation detail invisible to the inventory schema.
- Existing tests in `tests/test_blocks.py` remain valid; geometry assertions (volume, watertightness) will still pass because the epsilon is sub-resolution.
- No API or prompt changes required.
