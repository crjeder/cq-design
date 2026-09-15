## Context

`skill/phase3_build.md` is 80.8 KB and has grown on every one of 38 commits
since the 2026-07-16 SKILL.md split; a prior review of this session
identified instruction-surface growth as a plausible contributor to a
reported quality regression, but also found most of the file's content to be
load-bearing authoring guidance that cannot be safely cut without risking
the same regression from the other direction (losing needed instruction).
This change is deliberately narrow: three specific passages that restate,
word-for-word or table-for-table, content already guaranteed to be in the
orchestrator's context by the time that passage is read, per the file's own
Setup section.

## Goals / Non-Goals

**Goals:**
- Remove the three identified duplications with zero loss of instruction —
  every fact stays reachable, just not stated twice.
- Establish a citable rule (`skill-doc-structure`'s new requirement) so a
  future addition to `phase3_build.md` (or any phase file) has a named
  standard to check against instead of ad hoc judgment.

**Non-Goals:**
- Not a general prose diet. Not touching any authoring guidance, decision
  tree, CLI invocation, or JSON-contract description.
- Not touching the Gridfinity block subsection, which carries procedural
  instruction (mandatory reference read, archetype match, standalone
  check command) that `inventory.json` does not.
- Not changing the journal-append *mechanism* (format, milestone keys,
  `build/journal.md` semantics) — only how the instruction to append is
  presented in `phase3_build.md`.
- Not addressing `reference/scripts.md` vs `CLAUDE.md`'s per-script table
  overlap, or any other cross-file duplication outside this file — those
  are separate, unverified candidates from the earlier review and need their
  own read-through before cutting.

## Decisions

**D1: Citation, not deletion, for the XZ/-Y convention.** Step 4's
`disconnected_body` handling keeps its actionable instruction (read
per-body axis ranges; if they don't overlap on some axis, move the
misplaced body back, don't grow it to touch) and replaces only the inline
re-explanation of *why* `"XZ"`'s normal is `-Y` with "see `reference/CadQuery
Pattern Reference.md`'s Workplane Naming section" — that section is read at
Setup, unconditionally, before Step 1 of the first part. This mirrors the
citation pattern the file already uses for `{{CQ_REFERENCE}}` in inline mode
(same file, same precondition: "this read is the precondition for a
progressive part's inline citation").

**D2: Block tables become one pointer; Gridfinity subsection is untouched.**
`inventory.json`'s `name`/`use`/`params` fields are exactly what the four
plain tables (Primitives, Fasteners, Connectors, Joints) restate in
markdown. Alternative considered: trim the tables to a bare name list with
no `use` column. Rejected — that would lose information not recoverable
from `inventory.json` alone would be fine (it *is* recoverable, that's the
point), but a name-only list reads as more effort to act on ("go look each
one up") than a clean pointer ("this data is already read at Setup: see
`blocks/inventory.json`"), for the same byte cost. The Gridfinity
subsection is kept in full: `reference/gridfinity.md`'s mandatory-read
instruction, the archetype-match routing, and the standalone
`gridfinity_check.py` command are procedural content with no
`inventory.json` equivalent.

**D3: Journal blocks collapse to one line each, format preserved.** Each of
the seven `- phase3/<key>:<...>` fenced code blocks becomes one inline
sentence naming the exact line to append, keeping the literal format (so a
copy-paste-minded read still gets the right string) without the 3-line
fence overhead. This is NOT a citation to `skill/resume.md`'s Milestone
table, because `resume.md` is explicitly skipped on a fresh run ("On a
fresh directory with no journal, skip this file entirely") — the first-ever
append on a new project must not depend on a document that run path never
reads. `skill-doc-structure`'s new requirement's third scenario exists
specifically to record this distinction for future edits.

## Risks / Trade-offs

- [D1/D2's citations silently break if Setup's read list ever drops the
  cited document] → Mitigation: both citations name a document Setup
  already treats as a hard precondition for existing citations
  (`{{CQ_REFERENCE}}`, `inventory.json` per the Block library's own opening
  line "Select blocks in `blocks_needed` during planning..." which already
  assumes the inventory is available) — this change adds no new dependency
  on those reads, it reuses one the file already relies on elsewhere.
- [A reviewer skims the trimmed Block library section and can't quickly see
  which blocks exist without opening `inventory.json`] → Mitigation: keep
  the four category headers (Primitives / Fasteners / Connectors / Joints)
  with their module paths, drop only the per-block rows — a reader still
  sees the shape of the library, just not the full data.

## Migration Plan

1. Edit `skill/phase3_build.md`: Step 4 citation (D1), Block library tables
   (D2), seven journal blocks (D3).
2. `openspec/specs/skill-doc-structure/spec.md`: add the new requirement
   (this proposal's delta, applied at archive time).
3. No code, test, or schema changes. No rollback complexity beyond a normal
   revert of the prose edit.
