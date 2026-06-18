## 1. Create joints module

- [x] 1.1 Create `blocks/joints.py` with module docstring noting MIT-licensed geometry source
- [x] 1.2 Implement `dovetail_groove(width, wall, depth, length, angle=55.0)` — compute `inner = width - 2*wall`, build XZ trapezoid, extrude along +Y
- [x] 1.3 Implement `dovetail_tongue(width, wall, depth, length, angle=55.0, clearance=0.1)` — same profile with top and base width reduced by `2*clearance`

## 2. Update inventory

- [x] 2.1 Add `dovetail_groove` entry to `blocks/inventory.json` with correct `module`, `params` (including `wall`), `use`, and `sliding_interface` interface
- [x] 2.2 Add `dovetail_tongue` entry to `blocks/inventory.json` with `params` including `wall` and `clearance`, and `sliding_interface` interface
- [x] 2.3 Validate `blocks/inventory.json` against `blocks/inventory_schema.json` (run `blocks/validate.py` or equivalent)

## 3. Verify geometry

- [x] 3.1 Run `dovetail_groove(width=26, wall=3, depth=2, length=30)` and confirm: `zmin=0`, `zmax=2`, X-symmetric, `xmax - xmin` at opening = 20 mm
- [x] 3.2 Run `dovetail_tongue` with same args and confirm tongue X-span < groove X-span by exactly `2*clearance` at both Z=0 and Z=depth
- [x] 3.3 Confirm default angle=55 produces overhang of 35 degrees (flare = tan(35°) * depth)
- [x] 3.4 Export groove and tongue as STL and run `preview.py` to visually confirm the trapezoidal cross-section is correct orientation (wide at base, narrow at top)
