## 1. Reference content

- [x] 1.1 Add a "Flush-Fold Hinge Standoff" section to `reference/Engineering
      Design Rules.md`, tagged `<!-- applies_to: pin_hinge, living_hinge -->`:
      the standoff formula (standoff = pivot axis's perpendicular distance to the
      target plane), one-line derivation, clevis/tongue/standoff vocabulary, and
      the C5 cradle numeric worked example (`PIVOT_Y = 5mm`).
- [x] 1.2 State the formula's scope explicitly (exact +-90deg flush fold only) so
      the author knows not to apply it to arbitrary fold angles.

## 2. Selection-rule wiring

- [x] 2.1 Update `skill/phase3_build.md`'s `{{ENGINEERING_RULES}}` row (or
      adjoining prose) to state the additional-selection rule: select the
      flush-fold hinge section when the part declares a `kinematics` entry
      (block-based or block-free), mirroring the existing `load` special case.
- [x] 2.2 Sync `openspec/specs/reference-injection/spec.md` with this change's
      delta spec (via `openspec archive` at the end, not a manual edit now).

## 3. Verification

- [x] 3.1 Manually trace one block-based case (`pin_hinge`) and one block-free
      case (a `kinematics` entry with no `block`) through the phase3_build.md
      substitution rule and confirm both select the new section. Traced:
      block-based -- `applies_to: pin_hinge, living_hinge` intersects
      `blocks_needed: ["pin_hinge"]` -> selected. Block-free -- plan `kinematics`
      entry has `moving_union: "<part_id>"` and no `block`; new rule selects the
      section whenever this part id appears as some entry's `moving_union`,
      independent of `blocks_needed` -> selected.
- [x] 3.2 Confirm a part with neither `blocks_needed` hinge blocks nor a
      `kinematics` entry does not select the section (no regression on
      unrelated parts). Traced: e.g. `blocks_needed: ["screw_boss"]`, not named
      as `moving_union` in any `kinematics` entry -> `applies_to` intersection
      empty, not `always`, not named -> excluded.
