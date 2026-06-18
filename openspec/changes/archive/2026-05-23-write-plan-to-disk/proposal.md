## Why

After the planning phase generates and validates `BUILD_PLAN.json`, the skill only displays it as a code block - the user must save it manually before `orchestrate.py` can read it. This creates a silent gap: `--plan BUILD_PLAN.json` will fail with a file-not-found error unless the user knows to save the block themselves.

## What Changes

- The skill MUST write the validated `BUILD_PLAN.json` to disk in the working directory before asking for user approval.
- The skill MUST show the path it wrote alongside the JSON block so the user knows the file exists.
- If the user edits the file after approval, the skill re-validates from disk (already implied by current instructions, but now the file is guaranteed to exist).

## Capabilities

### New Capabilities

- `plan-disk-write`: Write the validated `BUILD_PLAN.json` to disk as part of Phase 2 (Planning), immediately after validation passes, before showing it to the user for review.

### Modified Capabilities

- `planning-phase`: Extend the "show plan to user" step to include a disk write before display.

## Impact

- `SKILL.md` Phase 2 section gains an explicit write step.
- `prompts/planning.md` is unchanged (it only governs the LLM output format).
- No changes to `src/orchestrate.py`, `src/plan_validate.py`, or any test files.
- No new dependencies.
