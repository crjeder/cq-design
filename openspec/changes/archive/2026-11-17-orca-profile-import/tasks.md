## 1. Schema

- [x] 1.1 Add optional `orca` block (app, data_dir, machine, process, process_purpose incl. `user`, filaments, processes, digest; all required, no extra props) to `src/printer_profile_schema.json`
- [x] 1.2 Add optional `build_volume_mm` {x, y, z > 0} to the schema
- [x] 1.3 Extend `tests/test_printer_profile_validate.py` for valid/incomplete `orca` and `build_volume_mm`

## 2. Fixture Orca tree

- [x] 2.1 Build `tests/fixtures/orca/Snapmaker_Orca/` with a trimmed system machine chain (Klipper, 4 nozzles), process chain (0.12/0.16/0.20/0.28 layers, compatible_printers), filament chain crossing into `OrcaFilamentLibrary`, a user process delta, a user filament delta, and a `.conf` whose leading JSON selects the machine
- [x] 2.2 Add a broken-chain preset (missing parent) for the error test

## 3. orca_profile.py core

- [x] 3.1 `discover`: OS config roots x {OrcaSlicer, Snapmaker_Orca, BambuStudio}, `system/` present, selected machine from `.conf` via `json.JSONDecoder().raw_decode`; `--data-dir` override
- [x] 3.2 Preset index (system + user, recursive, user shadows system) and `inherits` resolution with `missing_parent` / `inheritance_cycle` errors
- [x] 3.3 Value parsing helpers: list-of-string first element, `"N%"` to fraction, line width `"N%"` of nozzle
- [x] 3.4 Field mapping per design D4, including overhang `90 - t`, volumetric speed cap, `max_materials` from nozzle count, build volume from `printable_area`, `--max-materials` override, `orca.processes` list of every compatible process
- [x] 3.5 Junction deviation: `machine_max_junction_deviation` else Klipper SCV formula; verify the formula against Klipper docs before coding; omit `motion` when underivable
- [x] 3.6 Filament type -> material base-type map with `unmapped_material` error and `--material` override
- [x] 3.7 Digest (sha256 over resolved chain files in order) and `orca` block
- [x] 3.8 `import`: write mapped fields only (never the excluded calibration/policy fields), re-validate via `printer_profile_validate`, JSON output with written / skipped / compensation_warnings; `ambiguous_data_dir` when several installs and no `--data-dir`

## 4. Process selection and staleness

- [x] 4.1 `select-process --purpose {visual,functional,draft}`: compatible candidates, target fractions as module constants, tie-breaks per D6, reason string
- [x] 4.2 `--process <name>` override (purpose `user`, `incompatible_process` error) and `--write`
- [x] 4.3 `check`: `fresh` / `stale` (changed fields) / `unavailable` / `not_imported`, exit 0 for all

## 5. Tests

- [x] 5.1 `tests/test_orca_profile.py`: one test per spec scenario in `specs/orca-profile-import/spec.md` against the fixture tree
- [x] 5.2 Round-trip: import into `src/profile.default.json` copy validates and leaves `fit_clearance_mm` and `constraints.wall_min_mm` unchanged

## 6. Commands and prompts

- [x] 6.1 `commands/init.md`: after seeding, run discover + import (ask for filament from the compatible list, ask `--data-dir` when ambiguous, ask AMS/MMU slot count when the machine has one nozzle), report values, reason line and warnings; skip when profile pre-existed or no install
- [x] 6.2 New `commands/sync-profile.md` with `--machine/--process/--filament` passthrough and old -> new report
- [x] 6.3 `commands/status.md`: add `orca_profile.py check`
- [x] 6.4 `prompts/planning.md` (and `skill/phase2_planning.md` if it carries the summary format): planner picks from `orca.processes` and writes a `PROCESS: <name> | <purpose> | <why>` note; main session applies a differing pick unless `process_purpose` is `user`, shows reason line, applies a user-named preset with `--process`
- [x] 6.5 Add the new script to `src/skill_permissions.json` (forward-slash form, per the path-form memory) and `tests/test_init_permissions.py` if it pins the list

## 7. Docs and verification

- [x] 7.1 Contract entry in `reference/scripts.md`; line in `FILES.md`
- [x] 7.2 Check `.claude-plugin` / bundle manifests pick up the new command and script
- [x] 7.3 `uv run pytest tests/test_orca_profile.py tests/test_printer_profile_validate.py tests/test_init_permissions.py`; `ruff check` + `ruff format` on changed Python
- [x] 7.4 Manual run against the real Snapmaker Orca install: import, select-process visual, check
