## Context

`estampo_toml(stl_files, profile, flags)` already builds the overrides table from `profile.motion`. `wall_min_mm` lives in the plan's `constraints` (profile.json seeds it; the plan may override per model), and `deliverables.py` already reads plan constraints for the overhang flags. Support and brim are already per-part flags.

## Goals / Non-Goals

**Goals:**
- Emit a global `wall_loops` that realises the plan's minimum wall.

**Non-Goals:**
- Per-region or per-part wall thickness (open FEM TODO).
- Brim width/gap tuning, support style, infill pattern/direction.

## Decisions

- **`wall_loops = ceil(round(wall_min_mm / line_width_mm, 6))`**: rounding first stops 0.9/0.45 float noise adding a loop. Ceiling, because fewer loops would violate the stated minimum. Same quantity the FEM check treats as a physical thickness, so no new concept.
- **Source of `wall_min_mm`: the plan's constraints, passed as an argument to `write_estampo_toml`**, not read from the profile: the plan is the effective value (it may differ from profile.json), matching how `overhang_max_deg` is already passed.
- **Omit when `line_width_mm` or `wall_min_mm` is absent**, per the existing "never default" rule.
- **Global override, not per part**: estampo's per-part keys already used are `enable_support` and `brim_type`; no verified per-part wall key, so none is guessed.

## Risks / Trade-offs

- Orca's `wall_loops` counts perimeters at the process line width, which may differ from `motion.line_width_mm` -> the profile field is documented as the slicer's line width; mismatch only over-/under-shoots by a loop.
