# Design: gate-plan-validation

## Decision 1: Validate, don't guard

The TODO offers two fixes: "validate (or guard field access) before the kinematic stage."
Validate. `plan_validate.validate_plan` already encodes every constraint the kinematic
stage relies on -- the schema requires all nine kinematics fields, pins `axis_dir` to the
`X`/`Y`/`Z` enum, and shapes `required_range` as a 2-number array, and the cross-checks
verify `moving_union` is a real part, the block exists and carries a `dof`, and the unit
matches. Running it up front rejects exactly the plans that would otherwise crash
`kinematic_check`, with attributed messages the per-field guards could not produce.

Adding defensive `.get` guards inside `kinematic_check.py` as well would be redundant once
the gate refuses to call the stage with an invalid plan, and would duplicate validation
logic that already lives in one place. Keep the check trusting its (now validated) input.

## Decision 2: Where the validation runs

`run_gate` already reads the plan into a dict (`quality_gate.py:374`) and runs the
kinematic stage once, outside the fix loop (`quality_gate.py:438-439`). The plan-validation
stage goes in the same once-only region, before the kinematic stage. It needs the plan
*path* (not just the loaded dict) because `validate_plan(plan_path, ...)` re-reads and
schema-checks the file; `run_gate` already receives `plan_path`, so this is available.

The wrapper DFM and geometry/overhang stages run inside the fix loop and read the plan only
through defaulted lookups (`plan.get("constraints", {}).get(...)`, `plan.get("nozzle_mm",
0.4)`), so they cannot raise on a malformed plan and do not need to be gated. Only stages
that raw-index plan fields (today: the kinematic stage) are skipped on an invalid plan.

## Decision 3: Issue mapping and severity

`validate_plan` returns a `list[str]`. Each string becomes:

```
{
  "source": "plan",
  "severity": "error",
  "type": "plan_invalid",
  "message": <the validator string>,
  "hint": "Fix BUILD_PLAN.json so it passes plan validation (schema + cross-checks).",
}
```

`source: "plan"` is a new source value alongside the existing `wrapper`, `geometry`, and
`kinematics`; the issue contract is open (`source` is a free string consumed uniformly by
`_render_fix_prompt`), so no contract change is needed. `severity: "error"` blocks the
clean pass via the existing `passed = not errors` logic.

## Decision 4: Skip semantics

```
plan_issues = _run_plan_validation_stage(plan_path)
all_issues += plan_issues
if not any(i["severity"] == "error" for i in plan_issues):
    all_issues += _run_kinematic_stage(plan, stl_dir)
    # ... and any other plan-consuming stage
```

When the plan is invalid the kinematic stage is skipped entirely -- no STL load, no sweep,
no field access -- so the traceback path is unreachable. The gate still returns a normal
report (`passed: false`, the `plan_invalid` errors in `issues`), and the fix prompt
surfaces the validation messages so the planner can correct the plan.

A valid plan produces an empty `plan_issues` list, the kinematic stage runs exactly as it
does today, and the report is byte-for-byte unchanged.

## Decision 5: Inventory path

`validate_plan` defaults its `inventory_path` to `src/blocks/inventory.json`, the same file
`kinematic_check` and the gate already use. The stage calls `validate_plan(plan_path)` with
the default, keeping one source of truth for the inventory location.
