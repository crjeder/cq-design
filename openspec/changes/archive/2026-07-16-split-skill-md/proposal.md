## Why

SKILL.md is 71 KB (~17k tokens) and loads in full on every trigger, but most of its
content is phase-local: a `/render` or `/deliver` invocation pays for the entire
part-loop, planning, and hardware-table text it never uses. Improvement plan item 12
targets a <10 KB core that loads on trigger, with phase detail read only when that
phase starts.

## What Changes

- SKILL.md shrinks to the always-needed core: trigger, prerequisites, phase
  overview, JSON contract, error-handling reference, coordinate system, generated
  script rules, quick-reference file table, and per-phase pointers ("read
  `skill/phase3_build.md` when entering Phase 3").
- New `skill/` directory with per-phase files, moved verbatim (content is already
  written; this is a re-homing, not a rewrite):
  - `skill/phase1_requirements.md` - dimension lookup, web/Playwright search
    patterns
  - `skill/phase2_planning.md` - planning phase detail, /plan command specifics
  - `skill/phase3_build.md` - part loop detail, progressive build, orientation
    loop, kinematic validation walkthrough
  - `skill/phase4_deliver.md` - export and uv-project scaffolding, /deliver detail
- Hardware dimension tables move to `reference/hardware_dims.md`, read only when a
  fastener/hardware block is in `blocks_needed`.
- Each phase section in core SKILL.md becomes a short summary plus a mandatory
  "read this file first" instruction, so no phase runs on summary alone.

## Capabilities

### New Capabilities
- `skill-doc-structure`: progressive loading of skill documentation - what stays in
  the always-loaded core, what lives in per-phase files, and when each file MUST be
  read.

### Modified Capabilities

(none - no existing spec's requirements change; behavior of every phase is
preserved, only where its instructions live changes. `skill-invocation-path-
resolution` already covers resolving paths relative to SKILL_DIR, which the new
`skill/` files inherit.)

## Impact

- SKILL.md (major edit), new `skill/*.md` files, new `reference/hardware_dims.md`.
- CLAUDE.md file-layout section gains the `skill/` directory.
- No code changes; `src/` scripts are unaffected.
- Risk surface: a phase file not being read when its phase starts - mitigated by
  explicit MUST-read instructions at each phase boundary in the core.
