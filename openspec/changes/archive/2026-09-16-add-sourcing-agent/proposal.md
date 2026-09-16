## Why

Phase 0 sourcing triage (`skill/phase0_sourcing.md`) runs its web/Thingiverse/Printables/
MakerWorld search inline in the main session, so every page it opens accumulates in
main-session context. `ARCHITECTURE.md`'s own design rule states that "web page snapshots
... belong inside the agent that consumes them, so they never accumulate in the main
session" -- the Research agent already exists to enforce exactly this for Phase 1
dimension lookups (`prompts/research.md`, `render_research()`), but Phase 0 has no
equivalent and is not in the agent roster. `prompts/find_parts.md` is an orphaned,
never-wired-in file (not read by `render_prompt.py`, not referenced by
`skill/phase0_sourcing.md` or `ARCHITECTURE.md`) that reads like an abandoned first draft
toward exactly this agent.

## What Changes

- Add a **Sourcing agent**, structurally parallel to the Research agent: a new
  `prompts/sourcing.md` subagent prompt that runs the Phase 0 five-rung collect-then-
  classify search (web search, Thingiverse, Printables, MakerWorld, GitHub) against the
  seed corpus in `documentation/Block_Sources.md` section 2, and returns a structured
  candidate list (source, rung guess, license, notes) -- not raw page content.
- Add `render_sourcing()` to `src/render_prompt.py` (new `sourcing` subcommand), same
  shape as `render_research()`.
- Update `skill/phase0_sourcing.md`'s "Search workflow" section to dispatch to the
  Sourcing agent instead of running the search inline; the five-rung classification,
  license rules, and user confirmation (rung 3) stay in the main session as the
  decision/gate step, unchanged.
- Update `ARCHITECTURE.md`: add Sourcing to the agent roster table and the mermaid
  diagram, feeding Phase 0's classification step the same way the Research agent feeds
  the Phase 1 dimension checkpoint.
- Delete `prompts/find_parts.md` (superseded/absorbed by `prompts/sourcing.md`).
- **BREAKING**: none -- this changes internal pipeline structure only; `BUILD_PLAN.json`,
  the schema, and user-facing checkpoints are unaffected.

## Capabilities

### New Capabilities
- `sourcing-prompt-rendering`: `src/render_prompt.py`'s `sourcing` subcommand, rendering
  `prompts/sourcing.md` for the Phase 0 search agent.

### Modified Capabilities
- `sourcing-triage`: the Phase 0 search workflow moves from an inline main-session search
  (reusing Phase 1's workflow by reference) to a dispatched Sourcing agent call; the
  ladder, license, and provenance requirements are unchanged.
- `subagent-orchestration`: add a requirement that Phase 0 sourcing search runs as a
  sourcing agent, paralleling the existing "Dimension lookup runs as a research agent"
  requirement, and add Sourcing to the documented agent roster.

## Impact

- New file: `prompts/sourcing.md`.
- Modified: `src/render_prompt.py` (new `render_sourcing()` + CLI subcommand),
  `skill/phase0_sourcing.md` (dispatch instructions replace the inline "Search workflow"
  section), `ARCHITECTURE.md` (roster table + mermaid diagram).
- Deleted: `prompts/find_parts.md`.
- Tests: a `render_sourcing()` unit test alongside the existing `render_research()`
  coverage in `tests/test_render_prompt.py`.
- No schema change, no `BUILD_PLAN.json` field change, no user-facing checkpoint change.
