## Why

TODO.md's "C5 fixes did not take (2026-09-08)" documents one root cause behind
three reproduced defects in a long-lived real project: every merged guard
(`verify_seated`, `check_shared_interfaces`) is *prospective* — it only helps
a part that is re-planned or re-authored under the new rule. Nothing in
`plan_validate.py` / `script_lint.py` / `quality_gate.py` fails, or even
flags, a project for *missing* a guard that already existed when the part was
last touched. The 2026-09-08 C5 re-run reproduced a hinge boss buried past its
tangent plane (the exact shape `verify_seated`, merged Sep 1, exists to catch)
because the pre-existing `cradle.py` was only ever hand-edited, never
regenerated under the rule; it reproduced a re-diverged shared pivot literal
because `check_shared_interfaces`, merged Sep 7, only flags a *named*
`interfaces[].name` shared by two parts, and this plan's interfaces are
unnamed; and it re-litigated "which side is East" for the fifth time because
no field records a project's resolved compass binding, so every correction
round re-derives it from either the prompt default or buried request-log
prose and can land on either end.

This proposal implements items 1-3 of TODO.md's proposed retrofit work
(`#c5-fixes-did-not-take-2026-09-08`) — the absence-lints and the
`coordinate_frame` field — deliberately excluding item 4 (a `/retrofit`
command): the lints below already surface what a project lacks at the point
`plan_validate`/`quality_gate` already run, at no added step.

## What Changes

- Add `coordinate_frame` (`{east, north, up}`, each `+x/-x/+y/-y/+z/-z`) to
  `build_plan_schema.json`, defaulting to the `prompts/planning.md` standard
  binding when absent. `plan_validate.py` gains an advisory finding when
  `intent`/`planning_notes`/a `request_log` entry contains a compass term and
  no `coordinate_frame` is recorded on the plan.
- Add a `quality_gate.py` stage that flags a part script built for a
  `kinematics` entry of `type: "revolute"` (or a member of a `pin_hinge`
  `joints` entry) when the script's AST shows a boolean union with no call to
  `cq_verify.verify_seated`, `verify_backed`, or `blocks.joints.pin_hinge` —
  making the guard's *absence* on a pre-existing hand-rolled hinge script
  visible, advisory, at gate time.
- Broaden `plan_validate.check_shared_interfaces`: also flag two parts
  declaring round interfaces (`diameter_mm` within tolerance) at the same
  assembled-frame position (via each part's `placement`) with no `joints`
  entry linking them, even when `interfaces[].name` is null or the two names
  differ. Also flag a multi-part plan whose `intent`/`request_log` mentions a
  hinge/pivot/fold and has `joints: null` or `joints: []`.

## Capabilities

### New Capabilities
- `coordinate-frame`: per-project compass-to-axis binding, its schema field,
  and the plan_validate advisory for unrecorded compass usage.
- `hinge-guard-lint`: quality-gate stage detecting a revolute-kinematics part
  script that lacks the `verify_seated`/`verify_backed`/`pin_hinge` guard.
- `shared-literal-detection`: plan_validate advisory for two parts sharing an
  unlinked physical mate — a same-position/same-diameter round interface
  pair, or a plan with hinge/pivot language and no `joints` — extending
  (undocumented, unspecced) `check_shared_interfaces` beyond the named-only
  case it currently covers.

### Modified Capabilities
(none — `check_shared_interfaces`'s current named-interface behavior has no
existing spec file to delta against; `shared-literal-detection` above
captures both its existing and new behavior.)

## Impact

- `src/build_plan_schema.json`: new `coordinate_frame` property.
- `src/plan_validate.py`: `check_shared_interfaces` broadened;
  new `check_coordinate_frame_usage` (or equivalent) advisory function.
- `src/quality_gate.py`: new `_run_hinge_guard_stage`, wired into `run_gate`
  alongside the other advisory stages (`_run_edge_treatment_stage`,
  `_run_feature_presence_stage`).
- `src/units.py`: reuse `iter_unions`/`make_issue`; `src/placement.py`:
  reuse `transform_point` for the same-world-position comparison.
- `prompts/planning.md`: rule for writing `coordinate_frame` at the Phase 1
  exit checkpoint when the user's frame differs from the default; rule 7's
  shared-interface note extended to the unnamed case.
- `skill/phase1_requirements.md` / `skill/phase3_build.md`: checkpoint prose
  reads `coordinate_frame` instead of assuming +X = East.
- Tests: `tests/test_plan_validate.py` (schema + both broadened checks),
  `tests/test_quality_gate.py` (hinge-guard stage).
