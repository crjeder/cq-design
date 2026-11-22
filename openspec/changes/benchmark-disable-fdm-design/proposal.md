## Why

CADGenBench scores geometric fidelity to a nominal CAD model, not printability. The skill
adds FDM-specific design on top of the drawing: fit clearances, minimum wall thickness
(thickened walls), overhang/bridge fixes and breakaway fins, and a print-pose rotation of
the delivered files. These move the geometry away from the ground truth and lower the
score (#397). Today the only counter is prose in `evals/cadgenbench_run.py`'s `FIDELITY`
prompt ("do not add print clearances..."), which the planner and the quality gate do not
have to honor: the gate still blocks on `wall_min_mm` and overhang, and `build.py` still
rotates to print pose.

## What Changes

- New optional `profile.json` field `design_intent`: `"print"` (default, today's behavior)
  or `"cad"` (nominal geometry, no FDM-specific design).
- The planner copies `design_intent` into `BUILD_PLAN.json`. With `"cad"` the planning
  prompt drops the print rules: fit clearances, material wall allowances, printer wall
  minimums, overhang/bridge limits, and breakaway fins. Dimensions come from the request
  or drawing as given.
- With `"cad"` the quality gate skips the printability stages (min wall, thin regions,
  overhang, bridge, sliver, fin suggestions) and keeps the geometry stages (script runs,
  valid B-rep, watertight, bbox, features, plan probes).
- With `"cad"` `build.py` skips the print orientation and delivers every file in build
  pose (identity rotation).
- `evals/cadgenbench_run.py` writes `design_intent: "cad"` into each fixture's seeded
  `profile.json` and trims the `FIDELITY` prompt to the parts the switch does not cover
  (single solid, drawing is authoritative).

## Capabilities

### New Capabilities
- `design-intent-mode`: the `design_intent` profile/plan switch, and what it turns off in
  planning, the quality gate and `build.py`.

### Modified Capabilities
- `printer-profile-config`: the profile schema gains the optional `design_intent` field.

## Impact

- `src/printer_profile_schema.json`, `src/build_plan_schema.json` (new optional field).
- `prompts/planning.md`, `src/render_prompt.py` (conditional print rules).
- `src/quality_gate.py` (skip printability stages), `src/build_template.py` / `build/build.py`
  (identity orientation).
- `evals/cadgenbench_run.py`, `evals/README.md`, `reference/scripts.md`, `FILES.md`.
- Tests: `tests/test_plan.py`, `tests/test_cadgenbench_run.py`, a gate test and a build test.
- Default behavior unchanged for every existing profile and plan.
