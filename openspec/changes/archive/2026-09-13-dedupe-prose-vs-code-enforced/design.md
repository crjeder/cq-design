## Context

Prior dedup passes (see recent commits: "Dedupe CLAUDE.md's script index
against reference/scripts.md", "Trim duplicated narration from
skill/phase3_build.md") already removed doc-to-doc duplication. The remaining
duplication identified here is doc-to-code: prose in `SKILL.md` and
`skill/phase3_build.md` restates values a script or schema already owns
(typed error names/hints, lint check names, block inventory), so a code
change doesn't force a doc change and the two drift apart silently.

## Goals / Non-Goals

**Goals:**
- Replace restated code-owned facts with a pointer to the owning file.
- Keep enough prose that a reader still knows what category of error/check/
  block exists without opening the source file for routine work.

**Non-Goals:**
- Not touching doc-to-doc duplication (already covered by the existing
  skill-doc-structure requirement and prior commits).
- Not changing any script behavior, schema, or test.
- Not restructuring file layout (no new files beyond the spec delta).

## Decisions

- **Pointer + category summary, not a bare "see X" with zero content.**
  A reader mid-pipeline (e.g. hitting a `non_watertight` error) needs enough
  in SKILL.md to recognize the category and know where to look next; a bare
  file pointer with no context would send them hunting. So the error table
  shrinks to category + pointer, not deletion.
- **`reference/scripts.md` stays the single lint-check list**, since it
  already exists as that authority (confirmed by the audit) and
  `skill/phase3_build.md` is the only remaining restatement to cut.
- **Scope this as a `skill-doc-structure` delta**, reusing the existing
  capability rather than a new one, because it's the same doc-authority
  problem (avoid restating a source of truth) applied to code instead of
  another doc.

## Risks / Trade-offs

- [Shrinking the error table could make debugging slower if the pointer
  target is hard to scan] -> mitigate by keeping the hint *category*
  (e.g. "boolean/geometry failure", "print-orientation failure") inline, only
  dropping the exact wording and enumeration.
- [Future contributors might re-add restated detail out of habit] -> the new
  skill-doc-structure requirement gives future review something concrete to
  cite.

## Migration Plan

Single-pass doc edit, no rollout sequencing needed. Verify by grepping the
edited files for the removed enumerations/tables and confirming
`reference/scripts.md` / `run_cadquery_model.py` / `cq_verify.py` /
`blocks/inventory.json` remain the only place those values are listed.
