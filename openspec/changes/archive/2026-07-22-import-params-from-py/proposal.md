## Why

After a model is built, users routinely tweak dimensions by hand-editing the `PARAMETERS`
block of a generated part script (the fastest way to nudge a fit). `BUILD_PLAN.json` -- the
declared source of truth the validation gate checks against -- then silently drifts: a later
`plan_validate` or feature-presence check compares geometry against stale plan dimensions,
and any rebuild from the plan discards the user's edit. There is no way to fold a hand-edited
parameter back into the plan short of the user re-editing JSON by hand.

## What Changes

- Add a tool script `src/import_params.py` that parses a part script's `PARAMETERS` block
  (module-level numeric assignments, via `ast` -- no code execution, no CadQuery import) and
  reconciles the conventional dimension names (`width`/`depth`/`height`) back into that part's
  `dimensions.{w_mm,d_mm,h_mm}` in `BUILD_PLAN.json`.
- Emit a structured JSON report of every parameter read: which values changed the plan, which
  matched already, and which could not be mapped to a plan field (reported as advisory, never
  written blindly).
- CLI: `python src/import_params.py <part_script.py> --part <id> [--plan BUILD_PLAN.json] [--write]`.
  Default is a dry-run diff; `--write` re-validates the updated plan against the schema before
  persisting (reusing `plan_validate`'s validation), refusing to write an invalid plan.
- Document the round-trip step in `SKILL.md` so the workflow tells users to run it after a
  hand-edit rather than editing JSON directly.

## Capabilities

### New Capabilities
- `parameter-round-trip`: Re-import hand-edited part-script `PARAMETERS` values back into
  `BUILD_PLAN.json`, mapping the conventional dimension names to plan fields, reporting
  unmapped parameters as advisory, and refusing to persist a plan that fails schema validation.

### Modified Capabilities
<!-- None. This adds a standalone tool; it does not change requirements of existing specs. -->

## Impact

- New file: `src/import_params.py` (stdlib `ast` + `json` only; no CadQuery, no trimesh).
- New test file: `tests/test_import_params.py` (fast, no CadQuery -- same tier as
  `test_plan_validate.py`).
- Reuses `plan_validate`'s schema validation for the write-back guard.
- `SKILL.md`: one workflow note describing when and how to run the round-trip.
- No change to the `run_cadquery_model.py` JSON contract or any existing tool boundary.
