## Context

`build.py` (`src/build_template.py`) calls `model_export.export_model`, which always writes `model.3mf` and STLs; `formats` selects extras from `EXTRA_FORMATS` (step, obj, iges, scad). The profile is `printer_profile.json`, validated by `printer_profile_validate.py` against `printer_profile_schema.json`, seeded by `init_permissions.py`, and read by `fem_check`, `quality_gate`, `toolpath_speed`, `render_prompt`.

## Goals / Non-Goals

**Goals:** rename the file to `profile.json`; add `slicer.{preferred_format, slicer_name}`; make `build.py` fail loudly when no preferred format is configured.

**Non-Goals:** renaming the Python modules/schema file (`printer_profile_*`); G-code or slicer-specific export; using `slicer_name` for behavior; legacy fallback to the old filename.

## Decisions

- **Rename file only, not modules.** Keeps the diff to string/path changes; module names describe the schema, not the file. Alternative (rename everything) churns imports and the permission allowlist for no behavior gain.
- **`preferred_format` semantics: ensure-written, additive.** `3mf`/`stl` are always produced, so a preferred `3mf`/`stl` adds nothing; any other value is merged into `formats` (deduped) with `--formats`. Alternative (preferred format replaces the 3MF/STL outputs) would break the freshness/export manifest and gate consumers that read the STLs.
- **Format enum** = `{3mf, stl}` plus `EXTRA_FORMATS`, validated in the schema and re-checked in `build.py` so a hand-edited value fails clearly.
- **Required at build, optional in schema.** The `slicer` block stays optional so planning/gate scripts that never build keep working; `build.py` enforces presence. Within the block `preferred_format` is required.
- **Profile lookup in build.py**: `<project_root>/profile.json`, with `--profile` override. `bundle_project.py` must copy it into the project (verify it is not excluded).
- **Default seeds `"preferred_format": "3mf"` and a `slicer_name`** so fresh projects build. The name is a guess for the default printer (Snapmaker U1); the user edits it.
- **No legacy fallback**: a stale `printer_profile.json` is ignored and `build.py` reports the missing `profile.json`, with a hint if the old name exists.

## Risks / Trade-offs

- [Existing projects break at build] -> error message names the old file and the fix; documented as BREAKING.
- [Rename misses a string in docs/code] -> grep gate in tasks (`printer_profile.json` must have zero hits outside archive/changes).
- [`slicer_name` is unused] -> kept informational per request; shown in the build summary only.
