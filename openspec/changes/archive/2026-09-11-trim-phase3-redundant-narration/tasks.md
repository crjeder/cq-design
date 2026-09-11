## 1. Step 4: cite instead of restate the XZ/-Y convention

- [x] 1.1 In `skill/phase3_build.md` Step 4 item 1's `disconnected_body`
      paragraph, replace the inline re-explanation of why `"XZ"`'s normal is
      `-Y` with a citation to `reference/CadQuery Pattern Reference.md`'s
      "CadQuery Workplane Naming" section — keep the actionable instruction
      (read per-body axis ranges; move the misplaced body back rather than
      growing it to touch) verbatim.

## 2. Block library: pointer instead of restated tables

- [x] 2.1 Replace the Primitives, Fasteners, Connectors, and Joints tables
      under `## Block library` with one paragraph pointing to
      `blocks/inventory.json` (already read at Phase 3 Setup) — keep each
      category's header and module path (`src/blocks/primitives.py`, etc.).
- [x] 2.2 Leave the Gridfinity subsection untouched (its mandatory-read
      instruction, archetype-match routing, and standalone check command have
      no `inventory.json` equivalent).

## 3. Journal-append instructions: one line, format preserved

- [x] 3.1 Collapse each of the seven `build/journal.md` append fenced code
      blocks in `skill/phase3_build.md` to one inline sentence naming the
      literal line to append, preserving the exact `- <phase>/<milestone>:
      <fact>` string shown today.
- [x] 3.2 Do not cite `skill/resume.md` in place of the literal string — it
      is conditionally read (skipped on a fresh run) and must not be relied
      on for a fresh-run append.

## 4. Spec

- [x] 4.1 Confirm `specs/skill-doc-structure/spec.md`'s new requirement
      reads correctly against the three edits actually made (adjust wording
      only if an edit ended up not matching a scenario as written). Verified:
      all three edits match their scenarios as written, no wording change
      needed.

## 5. Verification

- [x] 5.1 Re-read the edited `skill/phase3_build.md` end to end: every fact
      removed is reachable from the cited source, no step's decision tree
      lost a branch, no CLI invocation or JSON field name changed.
- [x] 5.2 File size dropped from 80,759 B to 79,548 B (1,211 B removed) —
      less than the ~3.4 KB pre-implementation estimate, since the journal-
      block collapses (D3) kept the full literal append string inline by
      design (only the fence overhead was cut), and the Gridfinity table
      (unlike the four cut tables) was deliberately left in place per D2.
      Duplication removed with zero information loss, per the change's
      actual goal — the estimate was directional, not a target.
- [x] 5.3 `uv run pytest tests/` — 867 passed.
- [x] 5.4 `openspec validate trim-phase3-redundant-narration --strict` —
      valid.
