## Why

Printer, material, nozzle diameter, and DFM constraints (`wall_min_mm`, `overhang_max_deg`,
`dimension_tolerance_mm`) are currently re-entered or re-guessed every time the skill runs,
because `BUILD_PLAN.json` is the only place they're recorded and it's regenerated per model.
A user with a fixed printer setup has no way to state it once and have every future plan in
that directory default to it.

## What Changes

- Add a repo-root `printer_profile.json` (same directory as `BUILD_PLAN.json`) that holds a
  user's default `printer`, `material`, `nozzle_mm`, and `constraints`.
- Ship a default template inside the skill directory (`src/printer_profile.default.json`) and
  a schema (`src/printer_profile_schema.json`) for validating user edits.
- On first use in a directory (mirroring the existing permission-bootstrap check in
  `SKILL.md`), seed `./printer_profile.json` by copying the skill's default template if the
  file doesn't already exist, then tell the user where it is so they can edit it.
- Phase 1 (requirements gathering) and Phase 2 (planning prompt) SHALL read
  `printer_profile.json` when present and pre-fill `printer`, `material`, `nozzle_mm`, and
  `constraints` into `BUILD_PLAN.json` instead of asking the user or falling back to
  placeholder values. The user can still state a different value for a specific model; unless
  they flag it as a one-time exception, that value is written back into `printer_profile.json`
  as the new project-level default.

## Capabilities

### New Capabilities
- `printer-profile-config`: the repo-root `printer_profile.json` file -- its schema, the
  default template shipped with the skill, and the seed-on-first-use behavior that copies
  the default into a working directory that doesn't already have one.

### Modified Capabilities
- `planning-phase`: Phase 1 requirements gathering and the planning prompt now source
  `printer`, `material`, `nozzle_mm`, and `constraints` from `printer_profile.json` when it
  exists in the working directory, rather than always asking the user or using generic
  placeholder text.

## Impact

- `SKILL.md`: new bootstrap section (parallel to the permission-bootstrap section) that seeds
  `printer_profile.json`; Phase 1's requirements list updated to check the profile first.
- `prompts/planning.md`: gains a way to receive the resolved profile values (new placeholder,
  substituted by the skill before invoking the LLM, same mechanism as `{{FDM_GUIDELINES}}`).
- New files: `src/printer_profile.default.json`, `src/printer_profile_schema.json`.
- No change to `BUILD_PLAN.json`'s own schema or to any runtime `src/*.py` pipeline script --
  the profile is consumed only at prompt-rendering time, before the LLM call.
