## Why

The `planning.md` prompt produces BUILD_PLANs with underdefined clearances, free-text orientation fields that break down-pipeline vocabulary alignment, and no reasoning space for the LLM — leading to prints that don't fit together and parts generated against inconsistent assumptions.

## What Changes

- **Remove `print_orientation`** from schema, validator, orchestrator, and part prompt. Replace with a shared coordinate vocabulary (North=+Y, East=+X, South=-Y, West=-X, Up=+Z, Down=-Z). Print bed is always Z=0; the field was redundant. **BREAKING**: removes required field from BUILD_PLAN schema and all consumer code.
- **Add `planning_notes`** (string, optional, top-level): in-band reasoning space for the LLM before committing to JSON values.
- **Add `part_notes`** (string, optional, per-part): explanation for parts whose `blocks_needed` is empty or whose geometry is non-standard.
- **Differentiated clearance guidance**: replace the single 0.3–0.5 mm blanket range with a fit-type table (press=0.0, snap=0.15, sliding=0.25, loose/cover=0.5). `assembly.clearance_mm` remains the assembly-level default; each interface gains an optional `clearance_mm` override. Planning prompt instructs the LLM to extract preference from user request or ask interactively.
- **Interactive dimension fallback**: when a real-world dimension cannot be verified via web search, emit `-1` as placeholder and list it in `planning_notes`. The LLM asks the user in the interactive Claude Code session before finalizing the JSON.
- **Omit `assembly` for single-part models**: prompt explicitly states to omit the `assembly` key when `parts` has exactly one entry (schema already makes it optional).

## Capabilities

### New Capabilities

None — this change improves an existing capability only.

### Modified Capabilities

- `planning-phase`: requirements change for `print_orientation` removal (breaking schema change), new optional fields (`planning_notes`, `part_notes`, per-interface `clearance_mm`), differentiated clearance table, interactive dimension fallback, and single-part assembly-omit rule.

## Impact

- `prompts/planning.md` — primary rewrite
- `prompts/part.md` — remove `{{PRINT_ORIENTATION}}` slot, add coordinate vocabulary section
- `build_plan_schema.json` — remove `print_orientation` from part required fields and properties
- `plan_validate.py` — remove `print_orientation` from manual required-field check
- `orchestrate.py` — remove `{{PRINT_ORIENTATION}}` replacement in `_render_part_prompt`
- `tests/test_plan_validate.py` — update all fixtures that set `print_orientation`
- `tests/test_orchestrate.py` — update all fixtures that set `print_orientation`
- `openspec/changes/cad-skill-v2/specs/planning-phase/spec.md` — delta spec for changed requirements
