## 1. Schema

- [x] 1.1 Add optional `images` property to the `request_log` entry definition in
      `src/build_plan_schema.json`: array, `minItems: 1`, items are non-empty strings;
      keep `additionalProperties: false` and `required: ["ts", "kind", "text"]`
      unchanged (`images` stays optional).

## 2. Tests

- [x] 2.1 Add `test_request_log_entry_with_images_validates` to
      `tests/test_plan_validate.py`, following the existing
      `test_well_formed_request_log_validates` pattern.
- [x] 2.2 Add `test_request_log_empty_images_array_rejected` and
      `test_request_log_empty_image_path_rejected`, following the existing
      `test_request_log_empty_text_rejected` pattern.

## 3. Guidance

- [x] 3.1 Extend `skill/phase3_build.md`'s "Request log" section (Appending
      paragraph): when the user attaches an image to a clarification or correction,
      copy it into `sketches/` at the project root under `<slug>-<ts>.<ext>`
      (ts from the entry, colons replaced with `-`) before appending the entry, and
      set the entry's `images` field to the copied path.
- [x] 3.2 Extend the same section's "Searching" paragraph (or add a short adjacent
      note) instructing that when iterating on a feature during a correction round
      or Escalation, and the relevant `request_log` entry (found via
      `request_log_search.py`) carries `images`, read the referenced sketch file(s)
      before re-authoring -- the same discipline already prescribed for preview
      renders ("read the render before re-rendering", `skill/phase3_build.md`).
- [x] 3.3 Update `SKILL.md`'s existing one-line summary of `request_log`'s entry shape
      (`{ts, kind, text}`) to mention the optional `images` field, matching the level
      of detail already given there for the other fields.

## 4. Verification

- [x] 4.1 `uv run pytest tests/test_plan_validate.py -q`
