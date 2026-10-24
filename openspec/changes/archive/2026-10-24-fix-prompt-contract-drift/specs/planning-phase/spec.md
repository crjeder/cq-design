## ADDED Requirements

### Requirement: Planner compression-load instruction yields a schema-valid load
The planning prompt (`prompts/planning.md`, rule 10) SHALL instruct the planner to declare a resting/compressive part (base, plinth, foot, gasket, shim) or a non-load-bearing flat cover/panel as `load: {"dir": [0, 0, -1], "type": "compression"}`, so the emitted `load` satisfies `build_plan_schema.json`'s `required: ["dir"]`. The prompt SHALL state that the direction is ignored for strength scoring when the type is `compression`.

#### Scenario: Compression part passes plan validation
- **WHEN** the planner follows rule 10 for a base or flat cover
- **THEN** the part's `load` carries both `dir` and `type: "compression"` and plan validation reports no missing-`dir` error

#### Scenario: Prompt never shows a dir-less load
- **WHEN** `prompts/planning.md` is rendered
- **THEN** no instruction or example shows `load.type: "compression"` without an accompanying `dir`
