## 1. Rename

- [x] 1.1 `git mv src/printer_profile.default.json src/profile.default.json`; update `init_permissions.py` seed mapping and docstring
- [x] 1.2 Replace `printer_profile.json` with `profile.json` in `fem_check.py`, `quality_gate.py`, `toolpath_speed.py`, `render_prompt.py`, `printer_profile_validate.py` (paths, messages, CLI help)
- [x] 1.3 Update tests that write/read `printer_profile.json` (`test_fem_check`, `test_init_permissions`, `test_printer_profile_validate`, `test_quality_gate`, `test_render_prompt`)

## 2. Slicer block

- [x] 2.1 Add optional `slicer` object to `printer_profile_schema.json` (`preferred_format` enum required, `slicer_name` string, no extra props)
- [x] 2.2 Seed `slicer` in `src/profile.default.json`; allow `--set slicer.preferred_format=...` dotted keys in `printer_profile_validate.py`
- [x] 2.3 Schema tests: valid block, unknown format, block without format

## 3. build.py

- [x] 3.1 In `build_template.py` load `profile.json` (`--profile` override); exit 1 if file or `slicer.preferred_format` is missing/invalid (hint when old `printer_profile.json` exists)
- [x] 3.2 Merge preferred format into `formats` (skip `3mf`/`stl`, dedupe, keep `--formats` additive); print `slicer_name` in the summary
- [x] 3.3 Confirm `bundle_project.py` ships `profile.json`; add tests for configured, missing block, missing file, combined formats

## 4. Docs

- [x] 4.1 Update `SKILL.md`, `skill/phase*.md`, `prompts/*.md`, `README.md`, `CLAUDE.md`, `reference/scripts.md`
- [x] 4.2 Verify `git grep printer_profile.json` has no hits outside `openspec/changes/archive`; run `uv run pytest tests/`
