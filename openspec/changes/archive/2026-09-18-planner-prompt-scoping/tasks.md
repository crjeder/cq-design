## 1. Planning-scoped FDM tags

- [x] 1.1 Add `planning` to the `applies_to` tag of `Baseline & Tolerances`, `Print
      Orientation`, `Strength & Load Orientation`, and `Make It Adjustable (Tolerance
      Compensation)` in `reference/FDM 3D Print Design Guidelines.md`.
- [x] 1.2 Add a `scope: str = "always"` parameter to `tagged_sections` in
      `src/render_prompt.py`, replacing the hard-coded `"always" in tags` check.
- [x] 1.3 Update `render_planning`'s FDM `tagged_sections(...)` call to pass
      `scope="planning"`; leave `render_builder`'s two `tagged_sections(...)` calls (FDM
      and Engineering Design Rules) on the default.
- [x] 1.4 Update `tests/test_render_prompt.py` planning-prompt assertions to check for
      `planning`-tagged section presence and `always`-only (e.g. `Wall Thickness`)
      section absence from the planner prompt.
- [x] 1.5 Regenerate `build/planning_prompt.txt` (or run the existing render path) once
      and spot-check the char count drops as expected before/after.

## 2. Sourcing-agent license verdicts

- [x] 2.1 Move the license-rule prose (no-license = all-rights-reserved, ND blocks rungs
      1/2/4, rung-3 ND redistribution exception) from `skill/phase0_sourcing.md`'s
      License check section into `prompts/sourcing.md`.
- [x] 2.2 Add a `Reusable` column to `prompts/sourcing.md`'s return-contract table and
      example row, with the verdict vocabulary (`yes`, `no (all-rights-reserved / none
      stated)`, `no (ND)`, `rung-3-only (ND, redistribution permitted)`, `rung-3-only (ND,
      link only)`).
- [x] 2.3 Rewrite `skill/phase0_sourcing.md`'s License check section to trust the agent's
      `Reusable` verdict per candidate, keeping the provenance-recording instructions
      (license/URL/rung/verdict recorded in `planning_notes` or delivery summary)
      unchanged.
- [x] 2.4 Search the repo for anything else assuming the sourcing return table's prior
      5-column shape (docs, tests, other skill files) and update it for the new column.
- [x] 2.5 Update or add a `tests/test_render_prompt.py` (or equivalent) assertion that
      the rendered sourcing prompt contains the moved license-rule text and the
      `Reusable` column header.

## 3. Verification

- [x] 3.1 Run `uv run pytest tests/test_render_prompt.py` and confirm it passes.
- [x] 3.2 Run the full `uv run pytest tests/` suite once for a final sanity check.
- [x] 3.3 Diff `openspec/specs/reference-injection/spec.md` and
      `openspec/specs/sourcing-triage/spec.md` against this change's delta specs to
      confirm no unrelated requirement drifted before archiving.
