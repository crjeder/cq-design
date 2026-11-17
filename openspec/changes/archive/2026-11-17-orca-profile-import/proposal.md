## Why

`/cq-design:init` seeds a generic `profile.json` (Snapmaker U1, PLA, 0.2 mm layers, 5 s
min layer time) that the user must hand-edit, field by field, from numbers already stored
in their slicer. Most printer, process and filament fields can be read from the
OrcaSlicer-family profiles on disk, and a hand-copied profile silently drifts when the
user later edits their Orca presets.

## What Changes

- New `src/orca_profile.py` tool: finds an Orca-family slicer data dir (OrcaSlicer,
  Snapmaker Orca, Bambu Studio), resolves `inherits` chains, and maps machine, process
  and filament values onto `profile.json` fields.
- **Hybrid profile**: `profile.json` gains an `orca` block recording the source slicer,
  data dir, preset names (machine, process, filaments) and a digest of the resolved
  source files, alongside the resolved values written into the existing fields. The
  profile keeps working without Orca installed; the digest detects drift.
- **Process selection**: the tool picks the compatible process preset that best fits a
  print purpose (`visual`, `functional`, `draft`) and returns a one-line reason (e.g.
  "selected 0.16mm Standard (layer 0.16 mm) for visual quality"). Init selects for
  `functional`; the planner re-selects when the request's purpose differs and states the
  choice in the plan summary. The user can override by naming another preset.
- `/cq-design:init` runs the import after seeding when an Orca install is found and the
  profile has no `orca` block yet; with no install it keeps today's behavior.
- New `/cq-design:sync-profile` command: re-reads the recorded presets (or newly named
  ones), reports each changed field, and rewrites only Orca-sourced fields.
- `/cq-design:status` reports whether the Orca snapshot is stale.
- Profile schema gains optional `orca` and `build_volume_mm` blocks.
- Calibration and design-policy fields (`fit_clearance_mm`, `dimension_tolerance_mm`,
  `bridge_max_mm`, `wall_min_mm`, `interface_min_area_mm2`) are never written by the
  import.

## Capabilities

### New Capabilities
- `orca-profile-import`: discovering Orca-family slicer data, resolving preset
  inheritance, mapping values onto `profile.json`, process selection by purpose, and
  staleness detection.

### Modified Capabilities
- `printer-profile-config`: schema accepts `orca` and `build_volume_mm`; first-use
  seeding imports from Orca when available.
- `plugin-commands`: command set adds `sync-profile`; init runs the import; status
  reports Orca snapshot staleness.

## Impact

- New: `src/orca_profile.py`, `commands/sync-profile.md`, `tests/test_orca_profile.py`
  (fixture Orca tree under `tests/fixtures/orca/`).
- Changed: `src/printer_profile_schema.json`, `commands/init.md`, `commands/status.md`,
  `prompts/planning.md` (process selection line in the plan summary),
  `src/skill_permissions.json` (allow the new script), `FILES.md`,
  `reference/scripts.md`.
- No new dependencies (stdlib `json`, `hashlib`, `pathlib`).
- Existing profiles without an `orca` block validate and behave unchanged.
