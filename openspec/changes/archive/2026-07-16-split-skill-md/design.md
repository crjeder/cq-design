## Context

SKILL.md is 71 KB / ~1160 lines. Section audit (current headers):

| Section | Lines (approx) | Phase-local? |
|---|---|---|
| Trigger / Overview / Prerequisites | 1-142 | core (prereqs partly Phase-0-time) |
| Phase 1: Requirements gathering | 142-248 | yes -> phase1 file |
| Phase 2: Planning | 248-378 | yes -> phase2 file |
| Phase 3: Build | 378-822 | yes (largest) -> phase3 file |
| Phase 4: Deliver | 822-845 | yes -> phase4 file |
| /plan /deliver /render commands | 845-879 | core (entry points) |
| Block library | 879-916 | phase2/3 -> phase3 file, summary in core |
| Kinematic validation | 916-978 | yes -> phase3 file |
| DFM constraints | 978-1012 | core (quality gate contract) |
| Coordinate system | 1012-1025 | core |
| Generated script rules | 1025-1058 | core (part loop + gate both cite it) |
| Measurement: telemetry + evals | 1058-1082 | core summary, detail already in evals/ |
| Error handling reference | 1082-1102 | core (typed error table) |
| Hardware dimension reference | 1102-1158 | no phase - block-gated -> reference/ |
| Quick reference: key files | 1158-end | core |

Skills load SKILL.md in full at trigger time; everything else is read on demand
with the Read tool. The cost asymmetry is fixed and known (~17k tokens per
trigger), so the split criterion is purely "is this needed before knowing which
phase runs?"

## Goals / Non-Goals

**Goals:**
- Core SKILL.md under 10 KB; a `/render` or `/deliver` invocation costs ~2k tokens
  of skill text instead of ~17k.
- Zero content loss: phase files carry the moved sections verbatim.
- Deterministic loading: each phase boundary in the core carries a MUST-read
  pointer, so phase detail is always in context before the phase executes.

**Non-Goals:**
- No rewriting or condensing of the moved content (that is improvement plan item
  14, gated on telemetry).
- No change to prompts/, reference-injection behavior, or any src/ script.
- No phase0_sourcing.md yet - Phase 0 (sourcing triage, item 1) does not exist;
  the file is created when that phase lands.

## Decisions

1. **Split by phase, not by topic.** The reader is the orchestrating Claude at a
   known pipeline position; "what phase am I in" is the one question always
   answerable at read time. Alternative (topic files like `orientation.md`,
   `blocks.md`) rejected: it re-creates the discovery problem the trigger-load
   solves today.

2. **`skill/` directory, not `reference/`.** `reference/` is injected material for
   generated-part prompts (its own spec: reference-injection); `skill/` is
   orchestrator instructions. Mixing them risks phase instructions leaking into
   part prompts via the injection machinery. Hardware dimension tables are the one
   exception - they are lookup data, not instructions, and land in
   `reference/hardware_dims.md` gated on hardware blocks.

3. **Core keeps contracts, moves procedures.** Everything another component depends
   on stays core: JSON contract, typed-error table, DFM constraint values,
   coordinate system, generated-script rules, slash-command entry points. Step-by-
   step procedures (part loop, orientation loop, Playwright lookup flows) move.
   Rationale: contracts are needed to interpret any tool output regardless of
   phase; procedures are needed exactly once.

4. **MUST-read pointers with explicit paths.** Each phase section in core reduces
   to: 2-4 sentence summary, then "Before starting Phase N, read
   `skill/phaseN_*.md` in full." Mirrors the existing pattern the skill already
   uses for reference docs in Phase 3 setup. The phase file is read with the Read
   tool relative to SKILL_DIR (per the skill-invocation-path-resolution spec).

5. **Verbatim move first, no simultaneous editing.** The diff for this change is
   pure relocation plus pointer text. This keeps review tractable and separates
   the measurable token saving (this item) from content quality changes (item 14),
   so the eval harness attributes effects correctly.

## Risks / Trade-offs

- [Phase file skipped, phase runs on the summary] -> MUST-read language at every
  boundary; phase summaries deliberately omit operational detail (no step numbers,
  no commands) so running on summary alone fails fast and visibly.
- [Path drift if skill is relocated] -> paths are SKILL_DIR-relative, already
  specced by skill-invocation-path-resolution.
- [Extra Read round-trips per session] -> one Read per entered phase, a few hundred
  bytes of tool overhead against ~15k tokens saved on non-build invocations; a full
  4-phase run reads the same total content as today.
- [Docs referencing SKILL.md line numbers/sections break] -> CLAUDE.md and
  openspec specs cite section names, not line numbers; grep for `SKILL.md` in
  specs during implementation and update citations.

## Migration Plan

Single commit: create `skill/` + `reference/hardware_dims.md`, shrink SKILL.md,
update CLAUDE.md layout. Rollback is `git revert` (pure doc change). Verify with a
byte-count check (core < 10 KB) and a content-preservation diff (concatenated
phase files + core cover every removed section).

## Open Questions

- Whether the Prerequisites venv/seed bootstrap (~90 lines, shell blocks for three
  platforms) stays core or becomes `skill/setup.md` read on first-ever run. Default:
  move it; a triggered session in an already-seeded directory never needs it.
