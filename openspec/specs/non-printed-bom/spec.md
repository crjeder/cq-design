# non-printed-bom

## Purpose

Names everything the user must supply that a print does not produce -- screws, nuts,
washers, heat-set inserts, magnets, bearings, springs, filament/rod pins, adhesives -- in
the plan itself, the Phase 2 checkpoint, and the Phase 4 delivery, instead of leaving it
implied by which blocks a part happens to use.

## Requirements

### Requirement: Plan carries a bill of non-printed materials

`src/build_plan_schema.json` SHALL accept an optional top-level `bom` array. Each row SHALL
be an object with required `item` (non-empty string, e.g. `self-tapping screw`), required
`parts` (array of at least one part id string), optional `spec` (string, e.g. `M3 x 8`),
optional `qty` (integer >= 1, total across the listed parts), and optional `note` (string).
No other keys SHALL be accepted. A plan without `bom` SHALL validate unchanged.

#### Scenario: Plan with a bom row validates
- **WHEN** a plan has `bom: [{"item": "heat-set insert", "spec": "M3-0.5-6", "qty": 4, "parts": ["base"]}]` and a part `base`
- **THEN** `plan.py validate` reports no schema error

#### Scenario: Unknown key rejected
- **WHEN** a `bom` row carries a key `price`
- **THEN** `plan.py validate` reports a schema error at `bom -> 0`

#### Scenario: Zero quantity rejected
- **WHEN** a `bom` row has `qty: 0`
- **THEN** `plan.py validate` reports a schema error

#### Scenario: Plan without bom unaffected
- **WHEN** a plan omits `bom`
- **THEN** validation results are identical to before this change

### Requirement: bom rows reference existing parts

`plan.py validate` SHALL report a hard error for every `bom` row whose `parts` array names an
id absent from the plan's `parts[].id`.

#### Scenario: Unknown part id
- **WHEN** a `bom` row lists `parts: ["lid"]` and no part has id `lid`
- **THEN** `plan.py validate` exits 1 with an error naming row index and `lid`

### Requirement: Inventory marks blocks that consume supplied hardware

`src/blocks/inventory_schema.json` SHALL accept an optional `supplied_hardware` string on a
block entry naming what the user must supply for that block. `src/blocks/inventory.json`
SHALL set it on every block whose printed geometry is only usable with a non-printed item,
at minimum `screw_boss`, `pcb_standoff`, `heat_set_boss`, `hex_nut_trap`,
`counterbore_hole`, `countersink_hole` and `pin_hinge`.

#### Scenario: Hardware block carries the marker
- **WHEN** the inventory is loaded
- **THEN** `heat_set_boss` has a non-empty `supplied_hardware` value

#### Scenario: Purely printed block has no marker
- **WHEN** the inventory is loaded
- **THEN** `fillet_box` has no `supplied_hardware` key

### Requirement: Advisory finding for an unlisted hardware block

After a successful validate, `plan.py validate` SHALL print an advisory finding for every
part whose `blocks_needed` includes a block with `supplied_hardware` while no `bom` row lists
that part id in `parts`. The finding SHALL name the part, the block and the
`supplied_hardware` text. It SHALL NOT change the exit code.

#### Scenario: Missing bom row flagged
- **WHEN** part `base` lists `heat_set_boss` in `blocks_needed` and the plan has no `bom`
- **THEN** validate prints a finding naming `base`, `heat_set_boss` and its supplied item, and exits 0

#### Scenario: Listed part not flagged
- **WHEN** part `base` lists `heat_set_boss` and a `bom` row has `parts: ["base"]`
- **THEN** no bom finding is printed for `base`

### Requirement: Phase 2 summary renders the bom

`plan.py summary` SHALL render a **Non-printed hardware** Markdown table with columns Item,
Spec, Qty, Parts, Note when `bom` is non-empty, and SHALL omit the section otherwise.

#### Scenario: Table rendered
- **WHEN** the plan has one `bom` row
- **THEN** the summary contains a **Non-printed hardware** heading followed by a table with that row

#### Scenario: Section omitted
- **WHEN** the plan has no `bom`
- **THEN** the summary contains no **Non-printed hardware** heading

### Requirement: Delivery lists hardware to buy

`skill/phase4_deliver.md` SHALL instruct that, when `BUILD_PLAN.json` has a non-empty `bom`,
the delivery report and the generated `README.md` include a **Hardware to buy** section
listing every row (item, spec, qty, parts, note). The planner prompt SHALL direct
non-printed items into `bom` and keep only the assembly procedure in `planning_notes`
category (c).

#### Scenario: Delivery doc references bom
- **WHEN** `skill/phase4_deliver.md` is read
- **THEN** it names the `bom` field and the **Hardware to buy** README section

#### Scenario: Planner prompt routes hardware to bom
- **WHEN** `prompts/planning.md` is read
- **THEN** category (c) of the `planning_notes` rule names the assembly procedure only and a rule directs non-printed items into `bom`
