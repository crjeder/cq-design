## Why

Neither `BUILD_PLAN.json` nor the Phase 4 delivery names anything the user must buy or
supply. A user handed an enclosure built from `screw_boss` / `heat_set_boss` /
`pcb_standoff` is never told which screws or inserts to get, and a `pin_hinge`'s 1.75 mm
filament pin survives only as prose in `planning_notes` (surfaced by the 2026-08-12
`planning_notes` audit, C5 cross-check).

## What Changes

- New optional top-level `bom` array in `BUILD_PLAN.json`: one row per non-printed item
  (screws, nuts, washers, heat-set inserts, magnets, bearings, springs, filament/rod pins,
  adhesives), each with `item`, `spec`, `qty`, the consuming `parts`, and an optional `note`.
- New optional `supplied_hardware` field on `blocks/inventory.json` entries naming what a
  block needs from the user (e.g. `screw_boss` -> "self-tapping screw"). Set on the
  hardware-consuming blocks only.
- `plan.py validate`: hard error when a `bom` row names an unknown part id; advisory finding
  when a part uses a `supplied_hardware` block but no `bom` row lists that part.
- `plan.py summary`: renders a "Non-printed hardware" table at the Phase 2 checkpoint.
- Planner prompt: fill `bom`; `planning_notes` category (c) keeps the assembly procedure
  only and hands the hardware list to `bom`.
- Phase 4: the delivery report and the generated `README.md` carry a "Hardware to buy"
  section rendered from `bom`.

Not derived automatically from part scripts: `blocks_needed` carries block names only (no
params, no instance count), so a fully derived BOM would need runtime call recording. The
planner writes the rows; the inventory marker makes a forgotten row visible.

## Capabilities

### New Capabilities
- `non-printed-bom`: the plan's `bom` field, its validation and advisory cross-check against
  `supplied_hardware` blocks, and its rendering at the Phase 2 checkpoint and Phase 4
  delivery.

### Modified Capabilities
(none -- the new requirements live in `non-printed-bom`; `planning_notes` category (c)
wording is prompt text, not a spec requirement)

## Impact

- `src/build_plan_schema.json` (new `bom` property), `src/blocks/inventory_schema.json` +
  `src/blocks/inventory.json` (new optional field)
- `src/plan.py` (validate error + advisory, summary table)
- `prompts/planning.md`, `skill/phase4_deliver.md`
- `tests/test_plan.py`
- Backward compatible: `bom` is optional; existing plans and eval goldens validate unchanged.
