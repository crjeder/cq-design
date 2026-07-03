## 1. Schema and default template

- [x] 1.1 Create `src/printer_profile_schema.json` (JSON Schema draft-7) requiring `printer`
      (string), `material` (string), `nozzle_mm` (number), and `constraints` (object with
      required `wall_min_mm`, `overhang_max_deg`, `dimension_tolerance_mm`), mirroring the
      equivalent subset of `src/build_plan_schema.json`.
- [x] 1.2 Create `src/printer_profile.default.json` with placeholder `printer`/`material`
      values and `constraints` matching the existing example defaults in
      `prompts/planning.md` (`wall_min_mm: 1.2`, `overhang_max_deg: 45`,
      `dimension_tolerance_mm: 0.5`), validating cleanly against the new schema.

## 2. Validator and tests

- [x] 2.1 Create `src/printer_profile_validate.py` with a `validate_profile(profile_path,
      schema_path=...) -> list[str]` function following the shape of
      `src/plan_validate.py::validate_plan` (load JSON, validate against schema via
      `jsonschema`, return error strings; empty list = valid).
- [x] 2.2 Add `tests/test_printer_profile_validate.py` (schema-only, no CadQuery import,
      modeled on `tests/test_plan_validate.py`): valid profile passes, missing required
      field fails with a field-naming error, malformed JSON fails gracefully.
- [x] 2.3 Add a test asserting `src/printer_profile.default.json` validates against
      `src/printer_profile_schema.json`.
- [x] 2.4 Add a `write_profile_fields(profile_path, fields: dict) -> list[str]` helper to
      `src/printer_profile_validate.py` that merges only the given field(s) into the file on
      disk, re-validates the result, and returns validation errors (empty = written
      successfully); add a test covering partial-field merge and re-validation failure.

## 3. Bootstrap seeding in SKILL.md

- [x] 3.1 Add a "Printer profile bootstrap (first use per directory)" section to
      `SKILL.md`, placed after the existing permission-bootstrap section, with POSIX and
      PowerShell existence-checked copy commands (`printer_profile.json` from
      `$SKILL_DIR/src/printer_profile.default.json`, copy only if absent, never overwrite).
- [x] 3.2 State in that section that the skill announces the seed to the user in the same
      turn, with the path to edit.

## 4. Planning prompt and Phase 1 wiring

- [x] 4.1 Add a `{{PRINTER_PROFILE}}` placeholder section to `prompts/planning.md`,
      rendered from the validated profile's `printer`/`material`/`nozzle_mm`/`constraints`
      when present, describing to the LLM that these values are already decided and should
      populate the corresponding `BUILD_PLAN.json` fields directly.
- [x] 4.2 Update Phase 1's requirements-gathering list in `SKILL.md` (currently lines
      101-112) so printer/material/nozzle/constraints are read from a validated
      `printer_profile.json` first, only falling back to asking the user for a field that
      the profile doesn't supply or that fails validation.
- [x] 4.3 State the override rule: if the user explicitly states a different
      printer/material/nozzle/constraint for the current model, that value is used for the
      current `BUILD_PLAN.json` AND written back into `printer_profile.json` (only the
      stated field(s), leaving the rest untouched) as the new project-level default, with
      the update announced to the user in the same turn -- unless the user indicates it's a
      one-time exception, in which case the value is used for this model only and the file
      is left unchanged.

## 5. Documentation

- [x] 5.1 Add `printer_profile_schema.json`, `printer_profile.default.json`, and
      `printer_profile_validate.py` to the Core Scripts / File Layout tables in
      `CLAUDE.md`.
- [x] 5.2 Update `SKILL.md`'s "Quick reference: key files" section (if present) to list
      `printer_profile.json` alongside `BUILD_PLAN.json`.

## 6. Verification

- [x] 6.1 Run `uv run pytest tests/test_printer_profile_validate.py` and confirm it passes
      without a CadQuery import (fast, like `test_plan_validate.py`).
- [x] 6.2 Manually run the skill in a scratch directory with no `printer_profile.json` and
      confirm it gets seeded, then run it again and confirm the profile is read and Phase 1
      skips asking for printer/material/nozzle.
- [x] 6.3 Manually state a different nozzle diameter for one model and confirm
      `printer_profile.json` is updated with only that field changed and the skill announces
      the update; then state a value flagged as a one-time exception and confirm the file is
      left unchanged.
