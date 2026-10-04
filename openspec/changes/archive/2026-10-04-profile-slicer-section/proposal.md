## Why

`build.py` currently writes `model.3mf` plus STLs and only adds other formats when `--formats` is passed, so the deliverable format is never tied to what the user's slicer actually ingests. The profile also has no record of which slicer is in use. Making the output format a configured, required profile setting removes the guesswork and the per-run flag.

## What Changes

- **BREAKING**: rename `printer_profile.json` to `profile.json` (working-directory file, the seeded default `src/profile.default.json`, and every reader/writer that names the file).
- Add a `slicer` section to the profile with `preferred_format` (required within the section) and `slicer_name`.
- `build.py` reads `profile.json` and uses `slicer.preferred_format` as the default output: that format is always written alongside the existing `model.3mf`/STL deliverables. If `profile.json` or `slicer.preferred_format` is missing or invalid, `build.py` exits 1 with an error naming the missing setting.
- `--formats` stays as an additive override for extra formats.
- The default profile seeds a `slicer` block so fresh projects build out of the box.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `printer-profile-config`: file renamed to `profile.json`; new `slicer` block (`preferred_format`, `slicer_name`); `build.py` consumes it and fails when `preferred_format` is absent.

## Impact

- `src/printer_profile.default.json` -> `src/profile.default.json`, `src/printer_profile_schema.json` (new `slicer` block), `src/init_permissions.py` (seed name), `src/printer_profile_validate.py` (messages, dotted keys into `slicer`), `src/build_template.py` (load profile, resolve formats, error), readers in `src/fem_check.py`, `src/quality_gate.py`, `src/toolpath_speed.py`, `src/render_prompt.py`.
- `bundle_project.py` / working-directory docs: `profile.json` must travel with the bundled project so `build.py` can read it.
- Docs: `SKILL.md`, `skill/phase*.md`, `prompts/*.md`, `README.md`, `CLAUDE.md`, `reference/scripts.md`; tests that write `printer_profile.json`.
- Existing projects with `printer_profile.json` must rename it and add a `slicer` block (no legacy fallback).
