## Why

A plan-declared feature -- "a Ø4 mm port_cutout on the +X wall at (10, 15)" -- is today
verified only by the visual self-review: a VLM looks at a render and answers "is it
there?". That is the right tool for perceptual defects (wrong face, mirrored, wrong
shape) but a weak backstop for a fact the geometry can be *measured* to confirm. The
`disconnected_body` check (PR #45) already set the template: take an invariant that was
visual-only, give it a deterministic hard gate, and keep the visual question as the
human-legible cross-check. This change does the same for per-feature presence and
placement, adapting cad-khana's diagnostics-as-assertions idea to plan *intent* (not the
generic min-wall / clearance invariants, which are already covered by `thin_interface`,
`plate_clearance_check`, `keep_out_check`, `kinematic_check`, and the new `interference`
primitive).

## What Changes

- **Tighten the `interfaces[]` schema** so a feature's placement is machine-readable. The
  `planning-phase` spec already narrates `wall` / `position_mm` on an interface entry, but
  `src/build_plan_schema.json` requires only `type` and leaves the rest free-form
  (`additionalProperties: true`). Define structured, **optional** `wall`, `position_mm`,
  and a size field (`diameter_mm` / `size_mm`) so a declared position can be asserted
  against. Optional (not required) keeps existing plans valid and lets genuinely
  implicit-position features opt out. This is the prerequisite first step -- no assertion
  is possible without a structured target.
- **Add a deterministic feature-presence check** that, per part, confirms every interface
  entry which *declares a structured position* is realized by a matching feature at that
  position (within tolerance). Implemented at construction time by hooking the
  interface-emitting blocks and re-running the part script -- the `edge_treatment_check`
  pattern (wrap the API, re-run, attribute to a union) -- not by reverse-engineering the
  exported mesh. A declared-but-absent feature is a blocking finding; a present-but-drifted
  feature is a warning.
- **Layer with the visual review** (unchanged): the per-interface question in
  `reference/Visual Review Checklist.md` stays as the perceptual cross-check; this check is
  the deterministic backstop beneath it.

## Capabilities

### New Capabilities
- `feature-presence-validation`: the construction-time check that every plan-declared,
  structured-position interface feature is present at its declared position, emitting the
  shared gate contract (`error` for absent, `warning` for drift). First scope covers
  block-emitted features with a declared position; free-form / raw-geometry features are
  out of first scope.

### Modified Capabilities
- `planning-phase`: the `interfaces[]` entry schema gains structured, optional `wall`,
  `position_mm`, and size fields (machine-readable placement), replacing the current
  free-form `additionalProperties: true` shape. Behavior for existing plans is preserved
  (fields stay optional; an empty or position-less interface still validates).

## Impact

- `src/build_plan_schema.json`: structured optional `wall` / `position_mm` / size on
  interface entries; `src/plan_validate.py` if any cross-check is added.
- New `src/feature_presence_check.py`: block-hook + re-run per part, matched against that
  part's `interfaces[]`; wired into `src/quality_gate.py` as a once-outside-the-fix-loop
  stage (same wiring as `edge_treatment_check`).
- `blocks/`: the interface-emitting blocks (`port_cutout`, `cable_slot`, `vent_grid`,
  `screw_boss`, `pcb_standoff`, ...) must be hookable/attributable at apply-time; may need
  a light convention so a hooked call's authored-frame placement is recoverable.
- `prompts/planning.md` / `reference/`: guidance to emit structured positions when known.
- Tests: schema tests for the tightened interface shape; a feature-presence test that a
  declared port present at position passes, absent fails (error), and drifted warns.
- Out of scope: `assert_clearance` (proximity/gap, inverse of overlap; partly served by
  `plate_clearance_check`); assembly-clearance placeholder volumes (a cheap follow-up on
  the `interference` primitive); free-form/implicit-position feature assertions.
