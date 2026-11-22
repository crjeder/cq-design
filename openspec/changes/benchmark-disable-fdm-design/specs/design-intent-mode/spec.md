## ADDED Requirements

### Requirement: design_intent switch

`profile.json` and `BUILD_PLAN.json` SHALL accept an optional `design_intent` field with
value `"print"` or `"cad"`. An absent field SHALL mean `"print"`. The planner SHALL copy the
profile's value into the plan's top-level `design_intent`; the plan's value is the one the
gate and `build.py` read.

#### Scenario: Absent field
- **WHEN** a profile or plan has no `design_intent`
- **THEN** every stage behaves as it did before this capability

#### Scenario: Invalid value
- **WHEN** a profile or plan sets `design_intent` to any value other than `"print"` or `"cad"`
- **THEN** schema validation fails naming the field

### Requirement: CAD intent drops FDM design rules from planning

When `design_intent` is `"cad"`, the rendered planning prompt SHALL NOT instruct the planner
to add fit clearances, material wall allowances, printer wall minimums, overhang or bridge
limits, or breakaway fins. Dimensions SHALL come from the request or drawing as given.

#### Scenario: CAD prompt
- **WHEN** `render_prompt.py planner` runs with a profile whose `design_intent` is `"cad"`
- **THEN** the output contains none of the print-rule sections and states that nominal
  dimensions are used unmodified

#### Scenario: Print prompt unchanged
- **WHEN** `render_prompt.py planner` runs with `design_intent` `"print"` or absent
- **THEN** the output is identical to the output before this capability

### Requirement: CAD intent skips printability checks in the quality gate

When the plan's `design_intent` is `"cad"`, `quality_gate.py` SHALL NOT run the minimum-wall,
thin-region, overhang, bridge, sliver or fin-suggestion stages, and SHALL emit no issue from
them. It SHALL still run script execution, B-rep validity, watertightness, bounding box,
feature presence and plan-probe stages.

#### Scenario: Thin wall passes
- **WHEN** a part has a 0.8 mm wall, `wall_min_mm` is 1.2 and `design_intent` is `"cad"`
- **THEN** the gate reports no `wall_too_thin` or thin-region error

#### Scenario: Invalid geometry still fails
- **WHEN** a part's solid is not watertight and `design_intent` is `"cad"`
- **THEN** the gate still reports the watertight error

### Requirement: CAD intent delivers in build pose

When the plan's `design_intent` is `"cad"`, `build.py` SHALL NOT compute or apply a print
orientation, and every file it writes SHALL be in build pose.

#### Scenario: No rotation
- **WHEN** `build.py` delivers a part whose print orientation would otherwise tip it
- **AND** `design_intent` is `"cad"`
- **THEN** the delivered STEP's bounding box equals the part script's build-pose bounding box

### Requirement: CADGenBench runner selects CAD intent

`evals/cadgenbench_run.py` SHALL seed each fixture's work directory with a `profile.json`
whose `design_intent` is `"cad"`. Its prompt SHALL NOT repeat the print-clearance ban the switch covers, and SHALL keep the
single-solid, no-unshown-chamfer/fillet and drawing-is-authoritative rules.

#### Scenario: Seeded profile
- **WHEN** the runner prepares a fixture's work directory
- **THEN** its `profile.json` validates against `printer_profile_schema.json` and has
  `design_intent` `"cad"`
