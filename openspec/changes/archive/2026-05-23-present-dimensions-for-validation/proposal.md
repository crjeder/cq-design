## Why

During the planning phase, Claude looks up real-world product dimensions via Playwright and web search, then immediately embeds those values into `BUILD_PLAN.json`. The user has no checkpoint to review what was found before the plan is locked in — a wrong dimension (wrong model variant, ambiguous spec, unit error) silently propagates into generated geometry and wastes one or more full build cycles.

## What Changes

- After all dimension lookups are complete and before generating the JSON, the skill presents a structured "Dimensions Found" summary to the user.
- The summary lists each looked-up item, the value found, the source URL(s), and any conflicts or `-1` placeholders.
- The skill pauses for explicit user confirmation or correction before proceeding to generate `BUILD_PLAN.json`.
- If the user corrects a value, it is used in the plan instead of the looked-up value.

## Capabilities

### New Capabilities

- `dimension-validation-checkpoint`: A structured pause between dimension research and plan generation. The skill presents found dimensions with sources, waits for user approval or edits, and carries confirmed values forward into the plan.

### Modified Capabilities

- `planning-phase`: The requirements-gathering flow gains a mandatory confirmation step after dimension research and before plan generation. No schema changes; the behavior change is in SKILL.md.

## Impact

- `SKILL.md` Phase 1 and Phase 2 sections updated with checkpoint instructions.
- No changes to `prompts/planning.md`, schema, or any Python scripts.
- No breaking changes to `BUILD_PLAN.json` structure.
