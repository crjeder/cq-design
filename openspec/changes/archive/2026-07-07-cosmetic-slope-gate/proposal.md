## Why

Shallow up-facing surfaces (inclined roughly 5-45 degrees from horizontal) print as visible layer stair-steps and look bad. The pipeline already *measures* this -- `print_orientation.py` computes `gentle_incline_fraction` over that exact band -- but only uses it to rank orientations in `visual_quality` mode, buried in the score and never surfaced to the user. There is also no design-time guidance telling the generating model to avoid authoring such slopes in the first place, which is the real fix in a parametric-authoring pipeline.

## What Changes

- Add a warning-only quality-gate stage that reports the **up-facing** gentle-incline area of the chosen orientation, so the cosmetic problem is visible instead of hidden inside the orientation score.
- The finding fires **only when `optimize_for == "visual_quality"`** -- a shallow slope on a hidden structural face is a non-issue and must not nag.
- The finding is advisory (`severity: "warning"`), never an error: a shallow ramp still prints. It uses the shared quality-gate issue contract `{source, severity, type, message, hint, ...}`.
- Refine the detection to **up-facing faces only** (`nz > 0`) so it does not double-count down-facing shallow faces, which are overhangs (a separate, already-handled concern).
- Add an `always`-tagged design-guide section to `reference/FDM 3D Print Design Guidelines.md`: avoid shallow up-facing slopes; prefer >= 45 degrees or vertical; chamfer-step or lower layer height for the 20-45 degree range; note that layer height only buys smoothness in the ~20-45 degree part of the band.

Explicitly **out of scope** (deferred): the "Greedy Look-Ahead Filter" / chamfer-step profile transform (belongs with mesh/point-cloud reverse engineering, not parametric authoring); any auto-fix / fix-loop behavior (report-only for this first cut); a slope-aware layer-height recipe tweak.

## Capabilities

### New Capabilities
- `cosmetic-slope-detection`: whole-part detection of up-facing gentle-incline (cosmetic stair-step) area at the chosen print orientation, emitted as an advisory quality-gate finding gated on `visual_quality` intent.

### Modified Capabilities
<!-- None. The FDM design-guide section is content added under the existing
     reference-injection rules (an always-tagged section), which do not change.
     print-orientation-optimization's requirements are unchanged (its metric is
     reused, not altered). -->

## Impact

- **New code**: a detection function for up-facing gentle-incline area (a variant of `print_orientation.py`'s existing `_gentle_incline_fraction`, restricted to `nz > 0`), and a warning-only gate stage in `src/quality_gate.py` run once outside the fix loop, alongside the kinematic / plate-clearance / keep-out / edge-treatment stages.
- **Gate inputs**: needs the plan's `optimize_for` (per-part, else plan-level) and the chosen orientation for the part's union(s) (`build/orientations.json` / `--orientation`), which the gate already receives for the edge-treatment stage.
- **Reference content**: a new `always` section in `reference/FDM 3D Print Design Guidelines.md`, injected into planning and part prompts by the existing tag-filter mechanism.
- **Docs**: `CLAUDE.md` script table + file layout, `SKILL.md` gate-stage description, `TODO.md` item marked done.
- **No breaking changes**; no new dependencies (trimesh/numpy already present).
