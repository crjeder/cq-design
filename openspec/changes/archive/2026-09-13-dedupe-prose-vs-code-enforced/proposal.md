## Why

Several skill docs restate facts that a script already enforces mechanically:
`SKILL.md`'s error-handling table repeats every typed error name and hint text
that `run_cadquery_model.py`/`cq_verify.py` generate, `skill/phase3_build.md`
restates the exact AST lint-check list `script_lint.py` implements (duplicated
again in `reference/scripts.md`), and `skill/phase3_build.md` tabulates block
names/uses that `src/blocks/inventory.json` already owns -- in one spot even
right below a sentence telling the reader to look at inventory.json instead.
When the code changes (a new error type, a renamed lint check, an added
block), these prose copies go stale silently and nothing catches the drift.

## What Changes

- Shrink `SKILL.md`'s error-handling table to a short category list with a
  pointer to `run_cadquery_model.py`'s `errors[].hint` / `cq_verify.py` as the
  source of typed error names and remediation text, instead of restating each
  one.
- Replace the lint-rule prose list in `skill/phase3_build.md` with a pointer
  to `reference/scripts.md`'s `script_lint.py` entry (already the single
  authoritative list of check names).
- Remove the block-name list and Gridfinity block table in
  `skill/phase3_build.md` that restate `src/blocks/inventory.json`; keep only
  the procedural instruction ("check `inventory.json` before authoring") that
  has no machine-readable equivalent.
- Trim `CLAUDE.md`'s "Key Constraints" multi-union/thin-interface bullets
  down to naming the fields, deferring shape detail fully to
  `reference/scripts.md`.
- Add a requirement to the `skill-doc-structure` capability covering prose
  that duplicates a code-enforced contract (schema, typed error, lint check,
  or machine-readable inventory) specifically, distinct from its existing
  doc-to-doc duplication requirement.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-doc-structure`: add a requirement that phase-file and SKILL.md prose
  must not restate facts a JSON Schema, validator script, lint check, or
  machine-readable inventory file already enforces or defines -- such prose
  must cite the enforcing file instead of duplicating its content.

## Impact

- Docs only: `SKILL.md`, `skill/phase3_build.md`, `CLAUDE.md`. No source code
  under `src/` changes.
- No behavior change to any script; this is a documentation-drift-prevention
  change.
