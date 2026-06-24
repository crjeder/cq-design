## Why

Print orientation today has a single, fixed objective: strength first, minimal support
second. Real users care about different things on different parts — a bracket wants
strength, a throwaway jig wants the least support and fastest print, and a display piece
wants the best-looking surfaces. Visual quality has been neglected entirely. Users should
be able to ask the skill to prioritize one of three objectives per model (or per part)
instead of always getting the strength-first compromise.

## What Changes

- **Introduce three selectable optimization modes** for print-orientation selection:
  - `strength` (current behavior, remains the default): strength primary, support tiebreak.
  - `min_support`: minimize support primary, strength as the tiebreak.
  - `visual_quality` (new): optimize surface appearance — penalize gentle inclines
    (upward/downward faces sloped under 45 deg from horizontal, which stair-step visibly)
    and reward orienting the part's visible/cosmetic surface face-down against the smooth
    bed; strength then support break ties.
- **Add a `visual_score` (with components) to the optimizer output** alongside the existing
  `strength_score` and `support_score`, and make candidate selection mode-driven instead of
  a fixed lexicographic strength-then-support order.
- **Add an optional `show_face` declaration per part** (authored-frame outward normal of the
  primary cosmetic surface), mirroring how `load` works; inferred from geometry when omitted.
  This is what `visual_quality` orients face-down.
- **Add a plan-level `optimize_for` preference with optional per-part override**, so the user
  request ("optimize this for looks", "minimize supports") is recorded in `BUILD_PLAN.json`
  and drives the optimizer and the deliverable build script deterministically.
- **Plumb the mode through the tool boundary and re-runnable build script**: a
  `--optimize-for` flag (and `--show-face`) on `print_orientation.py`, and `build.py`
  recomputes orientations using the plan's recorded mode so regenerated plates match.

No change to the placement/assembled-frame pose, the JSON contract of
`run_cadquery_model.py`, or the kinematic/quality stages. Default behavior is unchanged
(mode defaults to `strength`).

## Capabilities

### Modified Capabilities
- `print-orientation-optimization`: selection is no longer a fixed strength-then-support
  order; it is chosen by a requested optimization mode (`strength`, `min_support`,
  `visual_quality`), and the optimizer gains a visual score (gentle-incline penalty +
  cosmetic-face-down reward) and a `show_face` input.
- `planning-phase`: `BUILD_PLAN.json` gains an `optimize_for` preference (plan-level with
  optional per-part override) and an optional per-part `show_face`, recorded from the user's
  stated priority during planning.

## Impact

- Code: `src/print_orientation.py` (scoring + mode-driven selection + new CLI flags),
  `src/build_plan_schema.json` (`optimize_for`, `show_face`), `src/plan_validate.py`
  (cross-checks for the new fields), `src/build_template.py` (recompute honoring the mode),
  `prompts/planning.md` and `SKILL.md` (record and act on the requested mode).
- Tests: `tests/` gains mode-selection and visual-scoring cases; `tests/test_plan_validate.py`
  gains `optimize_for`/`show_face` validation cases.
- No new runtime dependencies (trimesh + numpy already power the optimizer).
- Backward compatible: plans without `optimize_for` behave exactly as today.
