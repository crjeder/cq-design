## Why

The joint library covers rigid seams, articulated knuckle hinges, and ball joints,
but has no compact filament-pin hinge, no continuous flexure (living) hinge, and no
cosmetic seam detail for end-to-end butt joints. The previous joint pass deliberately
deferred the living hinge; this change adds it together with two adjacent
seam/fold features users keep reaching for on enclosures and folding parts.

## What Changes

- Add `filament_hinge`: a compact print-in-place hinge whose two leaves print flat
  as one body, interleaved knuckles bored for a snipped strand of 1.75 mm filament
  used as the pivot pin.
- Add `living_hinge`: two panels joined by a paper-thin continuous web that flexes,
  printed flat with the fold axis in the build plane.
- Add `shadow_gap`: an edge detail for parts that meet end-to-end, producing a
  deliberate ~1 mm recessed reveal on the visible face while a return wall hides the
  real seam behind it, so tolerance-driven gap irregularity is never visible.
- Extend the closed interface-type vocabulary and inventory schema enum with a new
  `seam` interface type for the shadow gap.
- Add inventory entries (with `motion`/`reversible`/`carries` taxonomy) and unit
  tests for all three blocks.

## Capabilities

### New Capabilities
- `filament-hinge`: compact print-in-place hinge piloted by a 1.75 mm filament strand pin.
- `living-hinge`: two panels joined by a thin flexure web that bends repeatedly.
- `shadow-gap`: end-to-end seam edge detail with a deliberate reveal hiding the real joint.

### Modified Capabilities
- `block-library`: the closed interface-type vocabulary gains the `seam` type.
- `joint-classification`: the inventory schema interface `type` enum gains `seam`.

## Impact

- `src/blocks/joints.py`: three new public functions (shared tiled-cylinder core reused
  for `filament_hinge`).
- `src/blocks/__init__.py`: re-export the three new blocks.
- `src/blocks/inventory.json`: three new descriptors.
- `src/blocks/inventory_schema.json`: add `seam` to the interface `type` enum.
- `tests/test_blocks.py`: geometry tests for the three blocks.
- No change to the runner, part loop, BUILD_PLAN schema, or quality gate.
