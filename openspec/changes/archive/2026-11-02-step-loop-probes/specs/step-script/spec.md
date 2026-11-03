## ADDED Requirements

### Requirement: Part scripts are an ordered step list
A part script SHALL build its geometry only through a `Part` recorder imported from
`blocks`, as an ordered list of steps. Each step SHALL be exactly one of `select`
(choose an inventory entry: block, template or primitive), `resize` (bind that entry's
parameters) or `place` (transform it and combine it with the host body using
`op` `base`, `union` or `cut`). The script SHALL end with `result = part.result()`.

#### Scenario: Block added in three steps
- **WHEN** a script adds a screw boss to a plate
- **THEN** it calls `part.select("screw_boss", id="boss")`, then `part.resize(boss)`,
  then `part.place(boss, at=..., op="union")`, and each call is one step in the step
  report

#### Scenario: Pattern placement is one step
- **WHEN** `place` is called with a list of four points
- **THEN** the four instances are combined in one `place` step and every instance's
  probes are added to the registry

### Requirement: Raw CadQuery is rejected in part scripts
`script_lint.py` SHALL report an error for any CadQuery call or `Workplane` method in a
part script. Allowed constructs SHALL be imports from `blocks` and `cq_verify`, `Part`
method calls, and plain arithmetic, comprehensions and loops used to compute positions.
A `PARAMETERS` block or any argument passed to `resize` SHALL be a lint error
(`script_dimension`), since dimensions are plan-owned.

#### Scenario: Raw extrude is a lint error
- **WHEN** a part script contains `cq.Workplane("XY").box(10, 10, 2)`
- **THEN** `script_lint.py` reports a `raw_cadquery` error naming the line, with a hint
  to use the `box` primitive

#### Scenario: Position arithmetic is allowed
- **WHEN** a script computes boss positions with a list comprehension and passes them to
  `place(at=...)`
- **THEN** `script_lint.py` reports no error for those lines

### Requirement: Primitives cover geometry no block provides
The inventory SHALL include primitive entries `box`, `cylinder`, `cone`, `sphere`,
`prism` (extrusion of a closed 2D polyline) and `revolve` (revolution of a closed 2D
polyline), each selectable, resizable and placeable like a block and each declaring
probes.

#### Scenario: Custom profile built from a prism
- **WHEN** a part needs an L-shaped bracket profile not covered by a block
- **THEN** the plan declares a `prism` instance whose `params` hold the polyline and
  extrusion depth, and the script selects, resizes and places it, with no raw CadQuery

### Requirement: Step scripts run unchanged outside the worker
Outside the step worker, `Part` SHALL execute each step eagerly so that the script is
plain Python and `run_cadquery_model.py`, `build.py`, the quality gate and
`CQ_PRINT_ROTATE` reloads run it with no change to their behaviour or JSON contracts.

#### Scenario: Cold run of a step script
- **WHEN** `run_cadquery_model.py` runs a step script without the worker
- **THEN** it produces the same `result` geometry as the worker run and the standard JSON
  contract

### Requirement: Resize reads parameters from the plan
`select(name, id=...)` SHALL bind the handle to the `blocks_needed` instance with that
`id` in the part's plan entry, and `resize(handle)` SHALL bind exactly that instance's
`params`. `part.param(id, name)` SHALL return a bound plan value for position
arithmetic. `resize` SHALL fail its step, before any geometry is built, when the
instance is missing from the plan, when a plan param is not declared by the entry, or
when a required param is missing. `Part` SHALL locate `BUILD_PLAN.json` from `CQ_PLAN`,
else by walking up from the script's directory.

#### Scenario: Values come from the plan
- **WHEN** the plan instance `boss` has `params: {"d_screw": 3.2, "d_outer": 8, "h": 6}`
- **THEN** `part.resize(boss)` builds the boss with those values and the step report
  lists them as resolved args

#### Scenario: Instance missing from the plan
- **WHEN** a script calls `part.select("box", id="rib")` and the plan has no `rib`
  instance
- **THEN** the `select` step fails with an error naming `rib` and the part's planned
  instance ids

#### Scenario: Misspelled plan parameter
- **WHEN** the plan instance has `d_scew` instead of `d_screw`
- **THEN** the `resize` step fails with an error naming `d_scew` and listing the entry's
  parameter names

#### Scenario: Plan edit changes geometry without a script edit
- **WHEN** the plan instance's `h` changes from 6 to 8 and the script is unchanged
- **THEN** the next run builds the boss 8 mm tall
