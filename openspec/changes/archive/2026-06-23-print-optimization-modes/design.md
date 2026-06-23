# Design

## Context

`src/print_orientation.py` enumerates stable bed-down candidates, scores each on
`strength` (load kept in the layer plane) and `support` (overhang area above
`overhang_max_deg`, bed contact as a tiebreaker), and selects with a fixed lexicographic
rule in `_select`: best strength, ties within `STRENGTH_BAND` broken by least support.
`SKILL.md` calls this objective "fixed and ordered". `build_template.py` recomputes the
same way when `orientations.json` is absent. The plan (`build_plan_schema.json`) carries a
per-part `load` but nothing about the user's optimization priority or which surface is
cosmetic.

We want the user to pick one of three objectives per model (optionally per part):
`strength` (today's behavior), `min_support`, and a new `visual_quality`. The mode must be
recorded in the plan so it is deterministic and survives into the re-runnable `build.py`.

## Goals / Non-Goals

Goals:
- Mode-driven candidate selection with `strength` as the unchanged default.
- A slicer-free visual score: penalize gentle inclines (<45 deg from horizontal) and reward
  the cosmetic surface facing the bed.
- Carry the requested mode (and optional `show_face`) through plan -> tool -> build.py
  deterministically.

Non-Goals:
- No slicer integration; the visual score stays a trimesh/numpy mesh proxy like the support
  score.
- No change to assembled-frame `placement`, the `run_cadquery_model.py` JSON contract, or the
  kinematic/quality stages.
- No automatic detection of "visible from the user's viewpoint" beyond the declared/inferred
  `show_face`.

## Decision 1: Mode is a plan field, threaded to the optimizer

Add `optimize_for` to `BUILD_PLAN.json` as a top-level preference
(`enum: [strength, min_support, visual_quality]`, default `strength`) with an optional
per-part override of the same name under each `parts[]` entry. The per-part value wins when
present, else the plan-level value, else `strength`.

`print_orientation.py` gains `--optimize-for {strength,min_support,visual_quality}`
(default `strength`) and `optimize_orientation(..., optimize_for="strength")`. The mode only
changes selection and which scores are reported as primary; all candidates are still scored
on every axis so the rationale can explain the trade-off.

`build_template.py` reads the effective mode per part from the plan when it recomputes an
orientation (the `orientations.json` reuse path is unaffected — it already holds the chosen
result), so regenerated plates match the delivered ones.

## Decision 2: Selection strategy per mode

`_select` becomes mode-aware. Each mode is a lexicographic ordering over the same scored
candidate dicts, with a tolerance band on the primary key so near-ties fall through to the
next key (preserving the existing anti-jitter behavior):

- `strength` (unchanged): primary `strength` (higher better, `STRENGTH_BAND`), then `support`
  (lower), then `bed_contact` (higher), then `idx`.
- `min_support`: primary `support` (lower better, a `SUPPORT_BAND` in mm2), then `strength`
  (higher), then `bed_contact` (higher), then `idx`.
- `visual_quality`: primary `visual` (higher better, a `VISUAL_BAND`), then `strength`
  (higher), then `support` (lower), then `idx`.

Determinism is preserved: same input + same mode -> same pick (final `idx` tiebreak stays).

## Decision 3: The visual score

For a candidate's posed mesh, compute two slicer-free components (both in [0, 1]) and
combine into `visual` = `cosmetic_down` minus a weighted `gentle_incline_fraction`:

- **Gentle-incline penalty.** For every face, the slope from horizontal is
  `theta = 90 - angle(normal, +Z)` ... more precisely the angle between the face normal and
  the build plane. A face stair-steps visibly when its normal is near vertical-ish but the
  surface is shallowly sloped: the bad zone is faces whose normal makes an angle with `+Z`
  (or `-Z`) inside `(FLAT_EPS_DEG, 45)` — i.e. neither near-flat (top/bottom, smooth) nor
  near-vertical walls (smooth). `gentle_incline_fraction` = (area of faces in that zone) /
  (total area). Faces resting on the bed are excluded (they are not visible). Lower is better.
- **Cosmetic-face-down reward.** `cosmetic_down` = `max(0, dot(show_face_after_rotation, -Z))`
  — 1.0 when the declared/inferred cosmetic normal points straight at the bed (smoothest
  first-layer finish), 0.0 when it points up or sideways.

`show_face` is an authored-frame outward normal supplied per part (`show_face.dir`, mirroring
`load.dir`); when omitted it is inferred as the outward normal of the largest planar face of
the mesh (the most likely "display" surface). The inferred direction is reported with a
`show_face_inferred` flag, exactly like `load_inferred`.

`visual = cosmetic_down - VISUAL_INCLINE_WEIGHT * gentle_incline_fraction`. Weight is a
module constant chosen so a fully-down cosmetic face is not overridden by a small amount of
incline area; both components are reported separately in the result for the rationale.

Rejected alternative: scoring "visible area" via ambient-occlusion/raycast visibility. Too
expensive and non-deterministic for a per-candidate inner loop; the declared/inferred
`show_face` plus the incline penalty captures the user's two stated rules directly.

## Output and rationale

`optimize_orientation` returns the existing keys plus `visual_score` (and its
`cosmetic_down` / `gentle_incline_fraction` components), `optimize_for`, `show_face` used,
and `show_face_inferred`. The `rationale` names the active mode and why the pose won under
it (e.g. "visual_quality: cosmetic face down (1.00), 3% gentle-incline area; strength 0.71,
support 12.4 mm2 as tiebreakers"). The emitted result remains distinct from `placement`.

## Risks / Trade-offs

- Inferring the cosmetic face as "largest planar face" can be wrong for organic parts; the
  `show_face` declaration is the escape hatch and the inference is reported so the design loop
  can correct it.
- `visual_quality` can pick a weaker/higher-support pose by design; that is the user's stated
  intent, and strength/support remain visible tiebreakers and in the rationale so the loop can
  fall back to `strength` if the trade is unacceptable.
- The incline "bad zone" threshold reuses 45 deg from the overhang convention for consistency;
  it is a module constant if tuning is needed later.

## Migration

Backward compatible. Plans without `optimize_for` validate and behave as `strength`. Existing
`orientations.json` files keep working (reuse path ignores mode). No data migration.
