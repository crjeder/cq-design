## Why

The planner can state geometric intent only indirectly: through an `interfaces[]` entry whose
`type` is in the fixed cut/boss table in `probes.py`. Request dimensions that do not fit that
table (a wall thickness, a lip height, "hole 6 mm from both edges", a floor that must stay
solid) never become a check, so the builder can silently invent or drop them. The probe
registry, the per-step re-check and the stuck rule already exist; the planner just has no
way to put its own assertions into them.

## What Changes

- `BUILD_PLAN.json` parts gain an optional `probes[]` array. Each entry is one of the
  existing body-evaluated probe kinds (`solid_at`, `empty_at`, `ray`, `bbox`) in build pose,
  with a required `label` quoting the request or plan fact it checks, and an optional
  `instance` naming the `blocks_needed` instance whose `place` step arms it.
- `probes.plan_probes()` seeds these authored probes into the registry alongside the
  interface-derived ones, plan-owned: never retired, not editable by the builder, part of
  the step cache key.
- `plan.py validate` rejects an authored probe whose `instance` is not a planned instance id
  (schema covers kind and field shape).
- The planning prompt gains one rule: every request number that locates or sizes a feature
  the interface table cannot express becomes a labelled probe; a wall or step height is
  bracketed by a `solid_at`/`empty_at` pair.
- No new probe kinds. `delta` stays step-only and is not accepted in the plan.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `probe-registry`: the step-0 plan-derived probes also include the part's authored
  `probes[]` entries, with the same plan-owned arming and no-retire rules.
- `planning-phase`: the BUILD_PLAN schema carries an optional per-part `probes[]`, and
  the planner turns otherwise-unprobed request dimensions into labelled probes.

## Impact

- `src/build_plan_schema.json`: new `parts[].probes` definition.
- `src/probes.py`: `plan_probes()` appends authored probes.
- `src/plan.py`: `_check_instances` also checks probe `instance` ids.
- `prompts/planning.md`: one new numbered rule plus an example.
- `reference/scripts.md`: probe field documented under the plan/probes contract.
- Tests: `tests/test_plan.py` (schema + instance check), a probe test that an authored
  probe fails on a body missing its feature.
- Only step scripts (`Part` recorder) evaluate plan probes; legacy part scripts are
  unaffected and remain out of scope.
