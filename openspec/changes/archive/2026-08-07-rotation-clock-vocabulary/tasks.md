## 1. Skill-phase documentation

- [x] 1.1 In `skill/phase2_planning.md`, next to the existing compass-convention rule, add
      the rotation-description rule: partial revolutions are stated as a clock position on
      the axis-paired view (above<->Z, South<->Y, West<->X), never "clockwise"/
      "counterclockwise", with the oblique-axis fallback (named start/end features).
- [x] 1.2 In `skill/phase3_build.md`'s kinematics/hinge section (where hinge sweeps and
      `dof`/`required_range` are surfaced to the user), add the same rule so checkpoint
      prose about a moving union's range follows it.

## 2. Verification

- [x] 2.1 Grep `skill/phase2_planning.md` and `skill/phase3_build.md` for "clockwise" and
      "counterclockwise" and confirm the only occurrences are the rule statement itself
      (explaining why the words are avoided), not example checkpoint prose using them.
- [x] 2.2 `openspec validate rotation-clock-vocabulary --strict` passes.
