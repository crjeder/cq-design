## Context

Shallow up-facing slopes stair-step visibly in FDM. `print_orientation.py` already poses
each candidate union mesh and, in `_gentle_incline_fraction`, computes each face's
inclination from horizontal to score `visual_quality` orientations -- but that metric is a
*fraction* of visible area, counts **both** up- and down-facing faces, and is consumed only
as an internal ranking score. The overhang check (`mesh_io.overhang_metrics`) already owns
the down-facing side. So the cosmetic up-facing concern is partially measured but never
surfaced, and there is no design-time guidance to avoid authoring the slope in the first
place.

The gate is invoked per part script and already receives the part's chosen print
orientation result via `--orientation` (used today for the print recipe and the
edge-treatment stage).

## Goals / Non-Goals

**Goals:**
- Surface up-facing gentle-incline (cosmetic stair-step) area at the chosen print
  orientation as an advisory (`warning`) gate finding, gated on `visual_quality` intent.
- Add an always-tagged FDM design-guide section so the generating model avoids the slope
  by design.
- Reuse existing posing + per-face slope math; do not duplicate mesh work.

**Non-Goals:**
- The "Greedy Look-Ahead Filter" / chamfer-step profile transform (deferred to the
  reverse-engineer-mesh work).
- Any auto-fix / fix-loop behavior. Report-only for this cut.
- A slope-aware layer-height recipe tweak.
- Changing `print_orientation.py`'s orientation *scoring* (the existing
  `gentle_incline_fraction` and `visual_score` stay byte-for-byte the same).

## Decisions

### Compute the metric in the print-orientation pass, surface it in the gate

`print_orientation.optimize_orientation` already poses the chosen mesh and computes each
face's slope. Add one more output to its result dict -- `cosmetic_slope_area_mm2`: the
absolute area of **up-facing** faces (`nz > 0` at the posed frame) whose inclination from
horizontal is in the open interval (`FLAT_EPS_DEG`, `GENTLE_INCLINE_MAX_DEG`) = (5, 45)
degrees, excluding bed-contact faces. The quality gate then reads this from the part's
orientation result (`--orientation`), and if the part's effective `optimize_for` is
`visual_quality` and the area exceeds a small threshold, emits one `warning` finding.

- **Why here, not a standalone check module?** Unlike the kinematic / keep-out /
  plate-clearance / edge-treatment stages (which need geometry the orientation step does
  not produce), this metric is a *byproduct* of work `print_orientation` already does. A
  standalone module would re-load and re-pose the union mesh purely to recompute a number
  the optimizer already had in hand.
- **Alternative considered:** reuse the already-stored `gentle_incline_fraction`. Rejected:
  it is a fraction (not area), and it counts down-facing faces, so it would double-count
  overhangs -- violating the spec's up-facing-only requirement.
- **Alternative considered:** a standalone stage that re-runs the part script (like
  `edge_treatment_check`) and applies the orientation rotation. Rejected as redundant
  posing work for a purely advisory number.

### Keep the up-facing slope math shared and testable

Put the up-facing gentle-incline area computation in a small `mesh_io` helper (alongside
`overhang_metrics` / `support_cost`), so it is unit-testable on a posed mesh independent of
the optimizer. `print_orientation` calls it for the new field; `_gentle_incline_fraction`
(the scoring path) is left untouched so orientation ranking does not shift.

### Gate reads intent and orientation from what it already has

The gate resolves the effective `optimize_for` (per-part, else plan-level) and reads
`cosmetic_slope_area_mm2` from the `--orientation` result. Gated on `visual_quality`; a
no-op otherwise. If the orientation result is absent or lacks the field, the stage emits a
`check_skipped` warning rather than measuring in the wrong (authored) frame. The stage runs
once, outside the fix loop, next to the other whole-part stages.

### The guide is content, not a spec change

The new FDM section is an `always`-tagged section injected by the existing
`reference-injection` rules. No injection behavior changes, so no delta spec for it.

## Risks / Trade-offs

- **Threshold tuning** (too low nags, too high misses) → advisory severity plus a
  conservative absolute-area default; the exact value is an implementation constant, easy
  to tune, and never blocks a build.
- **Only the chosen orientation is evaluated** → correct by intent: rotation is already
  tried by the optimizer; a residual warning tells the user the slope is unavoidable at the
  best pose, which is actionable (redesign / chamfer-step / lower layer height).
- **Band-edge flicker** (a ~45-degree face counted or not as pose shifts slightly) →
  acceptable for an advisory metric; the same tolerance already governs the optimizer's
  `gentle_incline_fraction`.
- **Adding a field to the orientation result** → additive and backward compatible; the
  recipe and `orientations.json` readers ignore unknown keys.

## Open Questions

- The exact `cosmetic_slope_area_mm2` reporting threshold (absolute mm^2, and whether to
  also express it as a fraction of visible area in the message).
