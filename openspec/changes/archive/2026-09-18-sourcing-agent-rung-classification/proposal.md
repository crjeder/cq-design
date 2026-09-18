## Why

`skill/phase0_sourcing.md` is 8.5K chars loaded into every Phase 0 pass. Most of it (rungs
1-5, ~85 lines) is the main session re-deriving a rung for each candidate the Sourcing
agent already read and described. The agent already classifies `Kind` (cadquery,
build123d, openscad, freecad, step, brep, iges, mesh) and license `Reusable` per
candidate — kind alone fixes rungs 1 and 2 deterministically, and the agent's page read
already tells it whether a mesh's stated dimensions match the request or need rework.
Having the main session re-walk the ladder from those same facts is duplicated judgment,
not verification.

## What Changes

- The Sourcing agent's return table gains a `Rung` column. For `Kind` in
  {cadquery, build123d, openscad, freecad} it returns `1`; for {step, brep, iges} it
  returns `2`. For `Kind: mesh` it returns a **provisional** rung — `3?` if the page's
  stated dimensions/description appear to match the request as-is, `4?` if a tractable
  discrepancy is named, or `n/a` if the mismatch looks freeform/organic (matching the
  existing rung 4→5 fallthrough rule).
- `skill/phase0_sourcing.md` stops restating the rung-1/2 selection logic (kind implies
  rung; trust the agent) and keeps only: the mesh-vetting steps that require local tool
  execution (`measure_stl.py`, quality gate stages, user confirmation) to turn a `3?`/`4?`
  provisional rung into a final one, and the per-rung handling instructions (how to
  reuse/import/rebuild) once a rung is confirmed.
- Rung 3's local vetting and mandatory user confirmation are unchanged — the agent has no
  Bash/measurement tools and cannot pass or fail the quality gate; its `3?`/`4?` is a
  hypothesis the main session still confirms or downgrades.
- No change to the license `Reusable` column or its rules (already agent-owned).

## Capabilities

### Modified Capabilities
- `sourcing-triage`: the decision ladder requirement changes from "Phase 0 classifies
  every candidate against the five rungs" to "the Sourcing agent assigns rungs 1/2
  deterministically from `Kind` and a provisional rung for mesh candidates; Phase 0
  confirms mesh provisional rungs via local vetting and applies the per-rung handling
  once a rung is final." `sourcing-prompt-rendering` is untouched: it governs how
  `render_prompt.py` fills `prompts/sourcing.md`'s placeholders, not the return
  contract's column list, which is prose content already inside that template.

## Impact

- `prompts/sourcing.md`: add `Rung` column to the return contract table and its
  assignment rules, next to the existing `Reusable` verdict rules.
- `skill/phase0_sourcing.md`: trim the rung-1/2 narrative, keep rung-3/4 vetting steps
  and per-rung handling instructions, add a short note on trusting the agent's `Rung`
  column the same way `Reusable` is already trusted.
- `src/render_prompt.py`: none expected (template substitution only; verify no
  hard-coded column list).
- `tests/test_render_prompt.py`: extend fixtures if the sourcing prompt template
  snapshot includes the return-contract table text.
- No change to `run_cadquery_model.py`, `measure_stl.py`, `quality_gate.py`, or the
  JSON/CLI contracts they emit.
