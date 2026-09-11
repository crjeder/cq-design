## Why

`CLAUDE.md` describes every `src/`/`evals/` script twice in its own body — once
in the "Core Scripts" table and again as an inline comment on the same file in
"File Layout" — and both restate, in a shorter and sometimes stale form, what
`reference/scripts.md` already documents in full. Three places to update per
script (add one, and the index table, the layout comment, and the reference
entry can all drift) is upkeep nobody asked for.

## What Changes

- Remove the standalone "Core Scripts" table from `CLAUDE.md`. `File Layout`
  already lists every script with a one-line comment in the same directory
  structure a reader needs anyway.
- Point the `File Layout` intro directly at `reference/scripts.md` for full
  per-script contract detail (JSON shapes, CLI flags, typed errors), instead
  of splitting that pointer across two sections.
- No content is removed from `reference/scripts.md` — it stays the single
  source of full script detail.

## Capabilities

### New Capabilities
- `claude-md-script-index`: `CLAUDE.md` carries exactly one one-line-per-script
  index (in `File Layout`), pointing to `reference/scripts.md` for full detail,
  so the two docs don't drift out of sync.

### Modified Capabilities
(none — no other spec requirements change)

## Impact

- `CLAUDE.md`: "Core Scripts" section removed; "File Layout" section's intro
  sentence updated to be the sole pointer to `reference/scripts.md`.
- `reference/scripts.md`: no changes.
- No code, tests, or runtime behavior affected.
