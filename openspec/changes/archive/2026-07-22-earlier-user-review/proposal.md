## Why

User review currently catches intent mismatches (wrong topology, wrong shape) only after
a part is fully authored and rendered -- expensive to correct, since a correction means
re-authoring the whole part. Progressive per-stage checkpoints already exist but are gated
behind a complexity heuristic, not offered by default, and there is no user-facing setting
for how often review happens; the "run autonomously" override is the only knob. Item 4 of
`IMPROVEMENT_PLAN.md`: move review earlier (before full authoring, via a cheap stub) and
make its frequency a declared, user-controlled policy instead of a hardcoded gate.

## What Changes

- Add a plan-level `review_policy` field (`minimal` | `checkpoints` | `every_stage`,
  default `every_stage`) to `BUILD_PLAN.json` that governs how often the part loop pauses
  for user review, replacing the existing ad hoc autonomous-run override.
- Add a Step 0 profile-stub render to the Phase 3 part loop: before authoring a part in
  full, generate and render a small stub (the part's characteristic 2D profile, extruded)
  and show it to the user for silhouette confirmation. User-facing by default; replaced by
  a self-review (no pause) only when `review_policy: minimal`.
- Change the progressive-build complexity gate (`openspec/specs/progressive-build/spec.md`)
  so its behavior is selected by `review_policy` rather than a hardcoded interfaces/blocks
  threshold: `every_stage` builds every part progressively, `checkpoints` uses today's
  complexity heuristic, `minimal` builds every part autonomously with no stage checkpoints.
- Planning prompt records `review_policy` from the user's stated preference, the same
  pattern already used for `optimize_for`.

## Capabilities

### New Capabilities
- `profile-stub-review`: Step 0 of the Phase 3 part loop -- render a cheap 2D-profile stub
  of a part before full authoring and pause for user silhouette confirmation, skipped (self-
  reviewed instead) under `review_policy: minimal`.

### Modified Capabilities
- `progressive-build`: the complexity gate that selects progressive vs. autonomous build is
  replaced by a `review_policy`-driven selection; the existing per-part/per-run override
  becomes redundant with `review_policy` and is superseded by it.
- `planning-phase`: `BUILD_PLAN.json` schema gains an optional plan-level `review_policy`
  field (`minimal` | `checkpoints` | `every_stage`, default `every_stage` when absent); the
  planning prompt records it from the user's stated review-frequency preference and the
  plan summary surfaces it.

## Impact

- `src/build_plan_schema.json` -- new `review_policy` enum field.
- `src/plan_validate.py` -- accept/default the new field (enum validation is schema-level).
- `prompts/planning.md` -- elicit and record `review_policy`; plan summary section.
- `skill/phase3_build.md` -- new Step 0 (stub render + checkpoint), progressive-build gate
  reworked to read `review_policy` instead of the complexity heuristic.
- `openspec/specs/progressive-build/spec.md` -- delta spec replacing the complexity-gate
  requirement.
- No change to `run_cadquery_model.py`'s JSON contract or to any block/exporter code.
