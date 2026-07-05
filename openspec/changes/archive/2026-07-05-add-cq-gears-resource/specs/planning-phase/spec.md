## ADDED Requirements

### Requirement: Planning phase surfaces cq_gears as an external resource when gears are needed
When the user's request or the resulting decomposition calls for gear geometry (e.g. a spur, helical, or other toothed gear, pinion, or gearbox part), and no block in `blocks_needed` provides gear geometry, the planning prompt SHALL note in `planning_notes` that `blocks/` has no gear block yet and point to `https://github.com/lwidm/cq_gears` as a downloadable external resource the user can install and use to generate the gear geometry themselves. This note SHALL NOT add a dependency, block, or schema field -- it is prose guidance surfaced to the user alongside the rest of `planning_notes`.

#### Scenario: Design includes a gear part
- **WHEN** the user's request describes a part that is a gear, pinion, or toothed gear component
- **THEN** the generated `BUILD_PLAN.json`'s `planning_notes` states that no gear block exists in the inventory and references `https://github.com/lwidm/cq_gears` as an external resource to generate the geometry

#### Scenario: Design has no gear parts
- **WHEN** the user's request contains no gear, pinion, or toothed-gear part
- **THEN** `planning_notes` contains no `cq_gears` reference

#### Scenario: Pointer does not add a dependency or block
- **WHEN** the gear pointer is surfaced in `planning_notes`
- **THEN** `pyproject.toml`, `blocks/inventory.json`, and the `BUILD_PLAN.json` schema are unaffected -- `blocks_needed` for the gear part is left empty or uses only inventory blocks, with the scratch-geometry rationale in `part_notes` as usual
