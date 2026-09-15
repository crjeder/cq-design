## Context

`CLAUDE.md`'s "Core Scripts" table and "File Layout" section both list every
`src/`/`evals/` script with a one-line description, and both exist alongside
`reference/scripts.md`'s full per-script contract detail. This is a same-file
editorial duplication with no architectural, cross-module, or behavioral
component — a single Markdown edit.

## Goals / Non-Goals

**Goals:**
- Keep exactly one one-line-per-script index in `CLAUDE.md` (the `File
  Layout` tree), and exactly one pointer to `reference/scripts.md` for full
  detail.
- Preserve every script currently listed — none are dropped, only the
  duplicate short description is removed.

**Non-Goals:**
- Restructuring `reference/scripts.md` itself.
- Changing which scripts exist or what they do.

## Decisions

- **Keep `File Layout`, drop `Core Scripts`** — `File Layout` already groups
  scripts by directory, which is more useful for navigation than a flat
  table, and its one-line comments carry the same information. Dropping the
  table (rather than the tree) loses no information.
- **Single pointer to `reference/scripts.md`** — move the "read this before
  modifying or calling any script" pointer to sit once, at the top of `File
  Layout`, instead of being stated in both sections.

## Risks / Trade-offs

- [A reader searching for a flat alphabetical script list won't find one] →
  the `File Layout` tree is already ordered by directory, which existing
  cross-references (e.g. `reference/scripts.md`'s own header) already assume
  as the canonical structure.

## Migration Plan

Single-commit doc edit to `CLAUDE.md`; no code or data migration.
