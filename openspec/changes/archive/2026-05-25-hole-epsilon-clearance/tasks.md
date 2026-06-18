## 1. fasteners.py

- [x] 1.1 Add `_EPS = 1e-4` constant at module level in `src/blocks/fasteners.py`
- [x] 1.2 Update `alignment_socket`: change `extrude(h)` to `extrude(h + _EPS)`
- [x] 1.3 Update `snap_socket_receiver`: change `extrude(h)` depth dimension to `depth + _EPS`
- [x] 1.4 Update `counterbore_hole`: change shaft `extrude(depth)` to `extrude(depth + _EPS)`
- [x] 1.5 Update `countersink_hole`: change shaft `extrude(depth)` to `extrude(depth + _EPS)`
- [x] 1.6 Update `hex_nut_trap` no-screw branch: change `extrude(depth)` to `extrude(depth + _EPS)`
- [x] 1.7 Update `hex_nut_trap` with-screw branch: change screw cylinder `extrude(depth)` to `extrude(depth + _EPS)`

## 2. connectors.py

- [x] 2.1 Add `_EPS = 1e-4` constant at module level in `src/blocks/connectors.py`
- [x] 2.2 Update `port_cutout`: change `box(..., depth, ...)` to `box(..., depth + _EPS, ...)`
- [x] 2.3 Update `cable_slot`: change `box(..., depth, ...)` to `box(..., depth + _EPS, ...)`
- [x] 2.4 Update `vent_grid`: change `extrude(depth)` to `extrude(depth + _EPS)`

## 3. Tests

- [x] 3.1 Run `uv run pytest tests/test_blocks.py` and confirm all tests pass
- [x] 3.2 If any volume assertions fail, widen tolerance to `1e-3` mm^3 and document the reason
