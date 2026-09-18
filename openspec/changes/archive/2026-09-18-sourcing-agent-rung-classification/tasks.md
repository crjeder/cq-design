## 1. Sourcing agent prompt

- [x] 1.1 Add a `Rung` column to `prompts/sourcing.md`'s return contract table, next to
      `Reusable`.
- [x] 1.2 Add the assignment rules: `Kind` in {cadquery, build123d, openscad, freecad} ->
      `1`; `Kind` in {step, brep, iges} -> `2`; `Kind: mesh` -> `3?` (stated dims/
      description match the request as-is), `4?` (tractable discrepancy named), or `n/a`
      (freeform/organic mismatch).
- [x] 1.3 Update the example row and the "Return an empty table" note if needed so the
      new column is unambiguous.

## 2. Phase 0 doc

- [x] 2.1 In `skill/phase0_sourcing.md`, cut the rung-1/rung-2 "how you know it fits"
      narrative (the kind -> rung reasoning) from rungs 1 and 2, keeping only the
      handling instructions (reuse/convert/import) that apply once a rung is taken.
- [x] 2.2 Add a short "trust the agent's `Rung` column for 1/2, treat `3?`/`4?` as
      provisional" note, mirroring the existing license `Reusable`-trust note.
- [x] 2.3 Confirm rung 3's vetting steps (`measure_stl.py`, quality gate stages, user
      confirmation) and rung 4's tractable-subset rebuild instructions are unchanged and
      now read as "confirming a provisional rung" rather than "classifying from
      scratch."

## 3. Tests

- [x] 3.1 Check `tests/test_render_prompt.py` for any sourcing-prompt snapshot/fixture
      that needs the new column text; update if present.
- [x] 3.2 Run `uv run pytest tests/test_render_prompt.py` and confirm it passes.

## 4. Spec sync

- [x] 4.1 Verify `openspec/specs/sourcing-triage/spec.md` will accept the delta cleanly
      via `openspec archive` once implemented (no drift from concurrent edits to that
      file).
