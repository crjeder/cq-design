## Context

`printer`, `material`, `nozzle_mm`, and `constraints` (`wall_min_mm`, `overhang_max_deg`,
`dimension_tolerance_mm`) currently live only inside `BUILD_PLAN.json`, which is regenerated
per model. Phase 1 of `SKILL.md` asks the user for printer/material/nozzle every run, and the
planning prompt's example schema (`prompts/planning.md:142-186`) hardcodes generic placeholder
defaults. There is already one precedent in this repo for "seed a working-directory file from
a skill-shipped default, once, idempotently": the permission bootstrap in `SKILL.md` (lines
59-97), which checks for `.claude/settings.local.json` via `src/init_permissions.py --check`
and merges in a default set if absent. This change follows the same shape for a new file.

## Goals / Non-Goals

**Goals:**
- Let a user state their printer setup once per project directory and have it reused across
  every planning session in that directory.
- Ship a sensible default so a fresh directory works immediately without requiring the user to
  hand-author the file first.
- Keep the profile optional and overridable: a user can state a different
  printer/material/nozzle/constraint for a specific model without hand-editing the file, and
  that statement becomes the new project-level default for the directory going forward.

**Non-Goals:**
- No cross-project (user-home-level) profile. If a user runs the skill across many project
  directories with the same printer, they re-seed each one; this can be revisited later if it
  becomes real friction.
- No printer hardware database (build volume, filament presets, per-printer slicer profiles).
  `orca-check`'s printer enum is a separate, pre-existing MCP concern and is not touched here.
- No change to `BUILD_PLAN.json`'s own schema, or to any `src/*.py` pipeline script that runs
  after planning. The profile is consumed once, at prompt-rendering time.

## Decisions

### File location: repo-root `printer_profile.json`, not a user-home file

Same directory as `BUILD_PLAN.json` and `build/`. Consistent with how this skill already
scopes all generated state to the invoking directory (see `SKILL.md:55-57`). A user-home file
was considered (avoids re-seeding per project) but rejected for now: it would need a
precedence rule against a repo-root override, and nothing in the codebase currently has any
cross-project state to model that after.

### Seeding: a plain existence-checked copy, no new merge-logic script

`src/init_permissions.py` exists because seeding `.claude/settings.local.json` is a *merge*
(add missing keys, preserve everything else, never reorder/duplicate). Seeding
`printer_profile.json` has no merge case — the file either exists (leave it alone) or it
doesn't (copy the default verbatim). This does not need a Python helper; `SKILL.md` gets a
bootstrap step structured like the permission-bootstrap check but using a plain
existence-then-copy instead of a merge:

```bash
if [ ! -f printer_profile.json ]; then
    cp "$SKILL_DIR/src/printer_profile.default.json" ./printer_profile.json
    echo "Seeded printer_profile.json with defaults -- edit it to match your printer."
fi
```

```powershell
if (-not (Test-Path printer_profile.json)) {
    Copy-Item "$SKILL_DIR/src/printer_profile.default.json" ./printer_profile.json
}
```

Alternative considered: extend `init_permissions.py` to also handle this file. Rejected —
it would mix two unrelated concerns (permission-pattern merging vs. static-file seeding) in
one script for no shared logic.

### Validation: a schema + a small validator, matching the rest of the pipeline's contract style

Every other structured input in this repo (`BUILD_PLAN.json`, `blocks/inventory.json`) has a
JSON Schema and a validator with test coverage (`plan_validate.py` / `test_plan_validate.py`,
`blocks/validate.py`). `printer_profile.json` gets the same treatment: `src/
printer_profile_schema.json` (draft-7, mirrors the `printer`/`material`/`nozzle_mm`/
`constraints` subset already required by `build_plan_schema.json`) plus a `src/
printer_profile_validate.py` with a `validate(profile: dict) -> list[str]` function, covered
by a fast schema-only test (`tests/test_printer_profile_validate.py`, modeled on the existing
`test_plan_validate.py`, no CadQuery import).

Alternative considered: skip programmatic validation and have Claude eyeball the file's JSON
at bootstrap time. Rejected — a malformed or partially-edited profile would silently propagate
bad values into every `BUILD_PLAN.json` generated in that directory with no test coverage of
the failure path, which doesn't match how every other input surface in this repo is handled.

### Delivery into the prompt: new `{{PRINTER_PROFILE}}` placeholder, substituted like `{{FDM_GUIDELINES}}`

The planning-phase spec already establishes the pattern: placeholders in `prompts/
planning.md` are substituted by the skill (Claude, inline) before the LLM call, not by any
runtime script. `{{PRINTER_PROFILE}}` follows `{{BLOCK_INVENTORY}}` / `{{FDM_GUIDELINES}}`:
when `printer_profile.json` validates, its resolved fields are rendered into the prompt and
Phase 1's requirements-gathering list skips asking for printer/material/nozzle/constraints.
When the file is absent, invalid, or the user explicitly states a different printer for this
model, Phase 1 falls back to today's ask-the-user behavior for exactly the fields in question
(not a full fallback to asking everything).

### Precedence: an explicit per-model statement overrides the profile and is written back to it

If the user says "for this one, use a 0.6mm nozzle instead," that value is used for the
current `BUILD_PLAN.json` AND written back into `printer_profile.json`, becoming the
project-level default for every subsequent model in that directory. Only the field(s) the
user explicitly restated are updated; fields the profile already supplied and the user didn't
mention are left as-is. The skill announces the write-back in the same turn ("updated
printer_profile.json: nozzle_mm -> 0.6") so the user sees the default has changed, not just
the current model.

Alternative considered: treat every stated value as a one-off that never touches the file
(the original design). Rejected per explicit direction: overrides are meant to update the
project-level default, not just the single model in front of the user. A user wanting a true
one-off exception without changing the project default must say so explicitly (e.g. "just for
this one, don't change the default"), in which case the skill uses the value for this model
only and does not write back.

## Risks / Trade-offs

- **Stale profile** (user changes printers but forgets to edit the file) → the existing
  plan-review gate (`planning-phase` spec: summary shows "Printer, material, and nozzle
  diameter" before the loop starts) already surfaces this for the user to catch before any
  code is generated. No new mitigation needed.
- **Schema/default drift** between `printer_profile_schema.json` and the equivalent subset of
  `build_plan_schema.json`, or between `printer_profile.default.json`'s constraint values and
  the example defaults already in `prompts/planning.md` (`wall_min_mm: 1.2`,
  `overhang_max_deg: 45`, `dimension_tolerance_mm: 0.5`) → keep the default template's values
  identical to the existing example defaults at authoring time; covered by the new unit test
  asserting the default file validates against its own schema.
- **Unprompted file creation** in the user's working directory → mitigated by only ever
  creating the file when absent (never overwriting), and announcing the seed in the same
  turn, mirroring how permission-bootstrap seeding is announced.
- **Unintended persistence**: a value the user meant as a one-off for a single odd model (e.g.
  a part being printed on a friend's printer) silently becomes the new project default →
  mitigated by always announcing the write-back in the same turn, and by honoring an explicit
  "just for this one" style statement as a true one-off that skips the write-back.

## Migration Plan

Purely additive. Directories without `printer_profile.json` get seeded on next skill
invocation and keep today's ask-the-user Phase 1 behavior for that first run (the profile
isn't consulted until it exists and validates). No existing file changes format or location.

## Open Questions

None blocking. Automatic seeding (vs. requiring an explicit opt-in command) mirrors the
existing permission-bootstrap precedent and is treated as resolved.
