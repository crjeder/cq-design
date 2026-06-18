## Why

The planning phase currently displays `BUILD_PLAN.json` as a raw JSON code block before asking for approval. JSON is hard to review at a glance -- a practitioner has to parse field names, nesting, and arrays mentally to understand what the plan actually says. A human-readable summary makes the approval step meaningful rather than ceremonial.

## What Changes

- The plan display step in Phase 2 is changed from a raw JSON dump to a structured human-readable summary
- The summary covers: part list with dimensions and blocks, printer/material settings, assembly strategy (if multi-part), interface list, and key constraints
- The raw JSON is still written to disk; it is no longer shown in the chat
- The written path and a prompt to approve or edit are still shown
- If the user edits the file on disk, re-validation from disk continues to apply

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `planning-phase`: The display format for the approval gate changes from raw JSON to a human-readable summary table/prose block

## Impact

- `SKILL.md` Phase 2 description updated to specify the human-readable format
- `openspec/specs/planning-phase/spec.md` requirement "Plan is shown to user for review" updated to require human-readable display, not JSON dump
