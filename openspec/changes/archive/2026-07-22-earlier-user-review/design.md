## Context

`skill/phase3_build.md`'s part loop currently has one review-frequency knob: a
complexity gate (`interfaces` non-empty OR `blocks_needed` count >= threshold) that
routes a part to progressive (staged, checkpointed) build; everything else builds
autonomously with review deferred to the end-of-part visual self-review. There is a
separate, informally-documented "autonomous run" override that skips checkpoints
altogether. Both are hardcoded behaviors, not something the user declares once per
plan. `openspec/specs/progressive-build/spec.md` and `openspec/specs/visual-self-
review/spec.md` already define the checkpoint and self-review mechanics this change
reuses; this change does not touch their stage/render/retry mechanics, only *when*
they fire.

## Goals / Non-Goals

**Goals:**
- Give the user one plan-level setting (`review_policy`) that determines review
  frequency for the whole part loop, replacing the complexity gate and the ad hoc
  autonomous override with one source of truth.
- Move the first review touchpoint earlier: a cheap profile-stub render before full
  part authoring, so a wrong silhouette is caught in seconds, not after a full part
  is built.
- Preserve the existing progressive-build stage mechanics and visual-self-review
  mechanics unchanged -- this change only decides when they run.

**Non-Goals:**
- Redesigning progressive build's stage order, checkpoint UI, or retry budget.
- Changing the visual self-review checklist or its questions.
- Per-part `review_policy` override (out of scope; plan-level only, matching
  `optimize_for`'s existing plan-level/per-part-override pattern is a possible
  future extension, not part of this change).
- Any change to `run_cadquery_model.py`'s JSON contract.

## Decisions

### `review_policy` has three values, default `every_stage`

- `minimal`: no stub checkpoint (self-reviewed instead), every part builds
  autonomously (today's "autonomous run" behavior). Fastest, least user
  interaction.
- `checkpoints`: stub checkpoint shown; progressive build applies only where
  today's complexity gate would already trigger it (interfaces present or
  blocks_needed over threshold). This preserves current default behavior for
  users who explicitly ask for it.
- `every_stage` (default): stub checkpoint shown; every part builds progressively,
  regardless of complexity.

Rationale for defaulting to `every_stage` rather than preserving today's gated
behavior as the default: item 4's stated goal is "review as often as possible at
moments review is cheap" as the default mode, with the complexity gate demoted to
an explicit opt-in (`checkpoints`). This is a deliberate behavior change, not just
a config knob addition -- called out explicitly in the proposal's "What Changes."

Alternative considered: keep the complexity gate as the default and add
`review_policy` only as an opt-in escape hatch (`minimal`/`every_stage` available,
default remains gated). Rejected because it doesn't satisfy the improvement plan's
explicit intent that progressive build become the default, not the exception.

### Profile stub is a real (tiny) authored-and-rendered artifact, not a mockup

The stub is a minimal CadQuery script: the part's characteristic 2D profile,
extruded to a nominal thickness, run through the same `run_cadquery_model.py
--preview` path progressive build already uses for stage previews. This reuses
existing rendering infrastructure (no new renderer) and gives the user a real
silhouette rather than a description. It is explicitly disposable -- not reused as
the base-shape stage of progressive build, since the stub's profile-only geometry
is not guaranteed to match the final base-shape construction plan (item 3's
staged construction contract).

Alternative considered: reuse the stub as progressive build's stage-1 output
directly. Rejected: coupling the two would force the stub's authoring approach to
match the eventual base-shape's construction plan, adding constraints to a step
meant to be cheap and throwaway.

### `minimal` self-reviews the stub instead of skipping it

Under `minimal`, Claude still generates the stub and evaluates it against intent
internally (no user pause), consistent with how autonomous parts already self-
review geometry today. This keeps the stub's error-catching value even in the
fastest mode, at near-zero added cost (the stub script and its `--preview` run are
cheap relative to full-part authoring).

### `review_policy` supersedes, does not compose with, the complexity gate

Rather than keeping both knobs, the complexity gate's threshold logic is preserved
verbatim but only consulted under `review_policy: checkpoints`. This avoids a
three-way interaction matrix (policy x gate x user override) and keeps the spec
delta small: `progressive-build`'s "complexity gate selects progressive or
autonomous build" requirement is replaced, not layered.

## Risks / Trade-offs

- [Default behavior change surprises existing users who relied on the complexity
  gate as-is] -> Mitigated by `checkpoints` reproducing that exact behavior as an
  explicit, one-word opt-out; document the default change in the plan summary
  (`review_policy` is always shown in the summary per `planning-phase`'s existing
  summary-section pattern).
- [Extra stub-render step adds latency to every part, even simple ones] -> Stub
  scripts are intentionally minimal (single profile extrusion); measure actual
  added time via `evals/` (item 8's harness) before further tuning, but do not
  block this change on that measurement since the harness is designed for exactly
  this kind of before/after check.
- [Stub geometry diverges from final part, teaching the user to distrust the
  checkpoint] -> Stub is explicitly scoped as silhouette-only confirmation
  ("does this outline look right"), not a preview of final features; the part
  loop's later stages and visual self-review remain the authority on feature
  correctness.

## Migration Plan

- Additive schema field with a default (`every_stage` when absent) -- existing
  `BUILD_PLAN.json` files without `review_policy` continue to validate and pick up
  the new default behavior on next build. No migration script needed.
- No rollback concerns beyond reverting the prompt/skill doc changes; nothing
  persists `review_policy` outside the plan file itself.

## Open Questions

- None outstanding; per-part override is explicitly deferred (see Non-Goals) rather
  than left open.
