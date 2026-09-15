## Why

`skill/phase3_build.md`'s "Post-delivery corrections" section is read on every Phase 3
run. Lines 276-283 keep the enforceable rule (re-run orientation/export/gate for
affected unions before re-reporting delivery) but also inline the incident narrative
explaining *why* the rule exists ("before this section existed, doing so was a judgment
call..."). That backstory already lives in full at
[TODO.md#silica-tray-re-export-coincidence](../../../TODO.md#silica-tray-re-export-coincidence).
Repeating it in the skill file costs tokens on every load without adding anything a link
doesn't already cover.

## What Changes

- Trim `skill/phase3_build.md`'s "Post-delivery corrections" section to state the rule
  plainly and link to `TODO.md#silica-tray-re-export-coincidence` for rationale, instead
  of restating the incident inline.
- No content is lost: `TODO.md` already carries the full backstory; only the duplicate
  copy in the skill file is removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None -- this is an editorial trim of skill documentation, not a change to any
documented requirement or behavior.

## Impact

- `skill/phase3_build.md` (Post-delivery corrections section only)
- No code, schema, or test changes
