## 1. render_prompt.py

- [x] 1.1 In `main()`'s builder branch, add `extra["model"] = part_author_model()`
      alongside the existing `extra["stages"] = part_stages` (`src/render_prompt.py:472`).

## 2. Skill docs

- [x] 2.1 Update `skill/phase3_build.md`'s Routing section: replace "`models.part_author`
      in `skill_config.json` (absent: Sonnet-class)" with reading Step 1's render
      output `model` field.

## 3. Tests

- [x] 3.1 In `tests/test_render_prompt.py`, assert the builder CLI's printed JSON
      contains a `model` key matching `part_author_model()`'s resolution, for both a
      configured `skill_config.json` and its absence.
