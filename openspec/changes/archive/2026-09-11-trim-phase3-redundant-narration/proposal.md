## Why

`skill/phase3_build.md` is read in full at the start of every build phase
(80,759 B, ~1,200 lines) and has only ever grown — 38 commits since the
2026-07-16 split, every one net-additive. This proposal does not attempt a
general prose diet (a prior review concluded that most of the file is
load-bearing authoring guidance, and cutting it risks the same
instruction-dilution quality drop this session started by investigating). It
cuts exactly three concrete, evidence-backed instances of **content
duplicated with something already guaranteed to be in context**, found by
reading the file in full:

1. Step 4's `disconnected_body` handling restates, in one 859-character
   sentence, the CadQuery workplane-normal convention that
   `reference/CadQuery Pattern Reference.md`'s "CadQuery Workplane Naming"
   section already states — and that reference is read into context once at
   Phase 3 Setup, unconditionally, before any part loop iteration.
2. The Block library's Primitives / Fasteners / Connectors / Joints tables
   (`name`, `use`, `params` per block) restate exactly the `name`/`use`/
   `params` fields of `blocks/inventory.json`, which Setup also reads into
   context unconditionally, in full, before the loop.
3. Seven of the file's `build/journal.md` append instructions repeat a
   3-line fenced bash code block for a milestone whose key, format, and
   "written when" description are already tabulated once in
   `skill/resume.md`'s Milestone table.

## What Changes

- Step 4 item 1's `disconnected_body` guidance keeps the actionable
  instruction (read the per-body axis ranges, move the misplaced body back)
  but replaces the inline restatement of the XZ/-Y normal convention with a
  citation to the already-in-context reference section.
- The Block library's four plain restatement tables (Primitives, Fasteners,
  Connectors, Joints — `src/blocks/{primitives,fasteners,connectors,joints}.py`)
  are replaced with one pointer to `blocks/inventory.json` (already read at
  Setup). The Gridfinity subsection is **not** touched — it carries
  procedural instruction (`reference/gridfinity.md` mandatory read, archetype
  match, the standalone conformance-check command) with no equivalent in
  `inventory.json`.
- The seven journal-append fenced code blocks collapse to one inline
  sentence each, naming the exact milestone line to append (format
  preserved, fence removed) — no change to what gets written to
  `build/journal.md`, only to how the instruction is presented.
- No behavior, JSON contract, CLI flag, or file layout changes. No code
  touched. Advisory/scoring/gate behavior is unaffected.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-doc-structure`: gains a new requirement — a phase file SHALL NOT
  restate content already guaranteed in context via that phase's Setup
  reads — that this change is the first instance of applying. (Additive to
  the existing spec; `skill-doc-structure`'s "content preservation"
  requirement, which governs the one-time SKILL.md -> phase-file split, is
  unaffected — that requirement is about not losing content across the
  split, not about freezing a phase file's wording thereafter.)

## Impact

- `skill/phase3_build.md`: the three edits above. Estimated reduction: ~700 B
  (Step 4 citation) + ~2,400 B (block tables) + ~350 B (journal blocks) ≈
  3.4 KB of the file's 80.8 KB — small, deliberately: this is a duplication
  cut, not a rewrite.
- No other file changes. No test changes (nothing in `tests/` reads
  `skill/*.md` prose).
