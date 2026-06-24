## Why

`quality_gate.run_gate` loads `BUILD_PLAN.json` with a bare `json.load` and never
validates it before handing it to the plan-consuming stages. The kinematic stage then
raw-indexes plan fields: `kinematic_check.py:191-192` reads `entry["required_range"]` and
`entry["moving_union"]`, and `_AXIS_VEC[entry["axis_dir"]]` (`kinematic_check.py:102`)
KeyErrors on any axis that is not `X`/`Y`/`Z`. A hand-written or partial plan -- one a
planner never ran through `plan_validate` -- therefore crashes the gate with a bare
Python traceback instead of the structured `{source, severity, type, message, hint}`
finding the rest of the gate emits. The gate is the safety net; a malformed plan should
fail it cleanly, not blow it up.

The project already has the validator: `plan_validate.validate_plan` runs the JSON Schema
(which requires every kinematics field and constrains `axis_dir` to the `X`/`Y`/`Z` enum
and `required_range` to a 2-number array) plus the inventory/placement/kinematics
cross-checks. The gate just never calls it.

## What Changes

- **Validate the plan once, up front, in the gate.** `run_gate` SHALL call
  `plan_validate.validate_plan` on the plan before running any stage that consumes plan
  fields beyond the constraint defaults it already reads safely. Validation runs once
  (outside the fix loop), like the kinematic stage.
- **Convert validation errors into the structured issue contract.** Each validation error
  string SHALL become an issue with `source: "plan"`, `severity: "error"`,
  `type: "plan_invalid"`, the validator's message, and a hint; these issues block a clean
  pass.
- **Skip plan-consuming stages when the plan is invalid.** When validation produces any
  error, the gate SHALL NOT run the kinematic stage (or any other stage that raw-indexes
  plan fields), so a malformed plan can never reach the code path that raises a bare
  traceback. The wrapper DFM and geometry/overhang stages, which read the plan only via
  defaulted `.get` lookups, are unaffected.
- **No behavior change for valid plans.** A plan that passes `validate_plan` SHALL produce
  exactly the same gate report it does today (same stages, same issues, same print
  recipe).

## Capabilities

### New Capabilities
- `gate-plan-validation`: the quality gate validates `BUILD_PLAN.json` with the shared
  plan validator before running plan-consuming stages, reporting any schema or cross-check
  failure as a structured `plan_invalid` error and skipping the plan-consuming stages, so
  a malformed plan fails the gate cleanly instead of raising a traceback.

## Impact

- Tooling: `src/quality_gate.py` -- add a plan-validation stage (call `validate_plan`,
  map errors to issues) and gate the kinematic stage (and any future plan-consuming stage)
  behind a valid plan. Reuses `src/plan_validate.py` as-is; no change to the validator.
- Specs: new `gate-plan-validation` capability. `overhang-analysis` and
  `kinematic-range-validation` are unaffected (this adds an up-front guard, not a change to
  those checks).
- Tests: extend `tests/test_quality_gate.py` (or a new file) -- a malformed-kinematics plan
  (e.g. `axis_dir: "XY"`, or a missing `required_range`) yields a `plan_invalid` error and
  no traceback, the kinematic stage does not run, and a valid plan's report is unchanged.
- Out of scope: changing what `plan_validate` checks, and adding defensive guards inside
  `kinematic_check.py` itself (the up-front gate validation is the on-design fix; per-field
  guards in the check would be redundant once the gate refuses to call it with an invalid
  plan).
