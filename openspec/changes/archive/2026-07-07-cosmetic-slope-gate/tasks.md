## 1. Up-facing slope metric (mesh_io + print_orientation)

- [x] 1.1 Add a `mesh_io` helper that returns the up-facing gentle-incline area (mm^2) of a posed mesh: faces with `nz > 0` whose inclination from horizontal (`arccos(nz)`) is strictly in (`FLAT_EPS_DEG`, `GENTLE_INCLINE_MAX_DEG`) = (5, 45) degrees, excluding bed-contact faces (down-facing near the floor). Keep the existing `overhang_metrics` / `support_cost` band/bed conventions.
- [x] 1.2 In `print_orientation.optimize_orientation`, compute the new helper for the chosen orientation's posed mesh and add `cosmetic_slope_area_mm2` to the returned result dict. Do NOT modify `_gentle_incline_fraction` or `visual_score` (orientation ranking must not shift).
- [x] 1.3 Unit tests for 1.1: an up-facing 30-degree ramp reports non-zero area; a down-facing 30-degree face reports zero (left to overhang); a flat top and a vertical wall report zero; a 45-degree face is excluded (open interval).

## 2. Gate stage (quality_gate)

- [x] 2.1 Add a `_run_cosmetic_slope_stage` in `src/quality_gate.py` that resolves the part's effective `optimize_for` (per-part else plan-level), and only for `visual_quality` reads `cosmetic_slope_area_mm2` from the `--orientation` result and emits one `warning` finding when it exceeds a small threshold constant. Use the shared `{source, severity, type, message, hint, ...}` contract (source/type `"cosmetic_slope"`).
- [x] 2.2 Degrade to a `check_skipped` warning when the effective mode is `visual_quality` but no orientation result / no `cosmetic_slope_area_mm2` is available; no-op (emit nothing) for non-`visual_quality` parts.
- [x] 2.3 Wire the stage into `run_gate` once outside the fix loop, alongside the kinematic / plate-clearance / keep-out / edge-treatment stages.
- [x] 2.4 Tests: `visual_quality` part with a shallow up-facing ramp yields one `cosmetic_slope` warning and the gate still passes; a `strength` part yields none; a `visual_quality` part with no orientation yields `check_skipped`; a per-part `visual_quality` override under a `strength` plan runs the check.

## 3. Design guide (FDM reference)

- [x] 3.1 Add an `always`-tagged section to `reference/FDM 3D Print Design Guidelines.md` (e.g. "Cosmetic Slopes / Stair-Stepping"): avoid shallow up-facing slopes; prefer >= 45 degrees or vertical; chamfer-step or lower layer height for the 20-45 degree range; note layer height only buys smoothness in the ~20-45 degree part of the band; point at print-orientation `visual_quality` and the overhang rule for the down-facing side.

## 4. Docs and closeout

- [x] 4.1 Update `CLAUDE.md` (quality_gate stage list + any new helper) and `SKILL.md` (gate-stage description paragraph) to document the cosmetic-slope stage.
- [x] 4.2 Mark the small-slopes item done in `TODO.md` with a one-line pointer to this change.
- [x] 4.3 Run `ruff check`/`ruff format` on changed Python and the full `pytest` suite; confirm green.
