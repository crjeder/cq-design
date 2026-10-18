## 1. Skill doc

- [x] 1.1 In `skill/phase0_sourcing.md` rung 3, extend step 1 to say: read `is_watertight` from the same `measure_stl.py` JSON; `false` (or a load failure) means rung 3 does not fit
- [x] 1.2 Replace step 2 with the exact command `uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/print_orientation.py" <path> --overhang-max-deg <n> --optimize-for min_support`, `<n>` from `profile.json` `constraints.overhang_max_deg`, and say to read `support_score` and `rotate`
- [x] 1.3 In step 3, add: a nonzero `support_score` is shown to the user as "needs support in its best pose" alongside the dimensions and license
- [x] 1.4 Reword the "fails measurement cross-check or either gate stage" bullet to "fails the measurement cross-check or is not watertight"; drop any remaining "quality gate" wording from rung 3

## 2. Check

- [x] 2.1 `grep -n "quality gate" skill/phase0_sourcing.md` shows no rung-3 hit, and ARCHITECTURE.md:44 still reads correctly
- [x] 2.2 Run the step-2 command once on any watertight STL in `tests/` to confirm it exits 0 and emits `support_score` and `rotate`
- [x] 2.3 `openspec validate rung3-mesh-vetting-commands` passes
