## 1. Skill doc

- [x] 1.1 Add "Requirements spec write, at approval" to
      `skill/phase1_requirements.md`, sibling to "Provenance write, at approval": write
      `REQUIREMENTS.md` at the project root (intent, topology, dimensions, fit,
      DFM constraints, open questions), same checkpoint turn as the `parameters.py`
      write.
- [x] 1.2 Document the skip condition (no topology ambiguity, no dimension lookups, no
      stated fit type) and that Phase 2 amends the file in place rather than
      regenerating it.
- [x] 1.3 Document the `build/journal.md` milestone line,
      `phase1/requirements_written`, and that it is skipped whenever the file itself is
      skipped.

## 2. Phase 2 cross-reference

- [x] 2.1 In `skill/phase2_planning.md`, add one line alongside the existing
      `parameters.py`-amend instruction noting that `REQUIREMENTS.md` is amended
      in place under the same condition (planning introduces or changes a
      requirement), so the two files don't drift out of sync procedurally.

## 3. Docs

- [x] 3.1 Add `REQUIREMENTS.md` to the project-root artifacts Phase 4's delivery
      summary points to (`skill/phase4_deliver.md`), alongside the existing
      `parameters.py` pointer.
- [x] 3.2 Skipped: `CLAUDE.md`'s File Layout documents the skill's own source tree,
      not generated per-project artifacts -- `parameters.py` isn't listed there either,
      so adding `REQUIREMENTS.md` would be inconsistent with the existing convention.
