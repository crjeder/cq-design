## Context

`ARCHITECTURE.md` documents a sub-agent split with two forces driving every agent
boundary: user interaction stays in the main session, and context-heavy payloads (web
page snapshots, preview images) stay inside the agent that consumes them. The Research
agent (`prompts/research.md`, `render_research()`) already implements this for Phase 1
dimension lookups: it browses spec pages, community-model listings, and (when needed)
downloads and measures an STL, returning only a validation table.

Phase 0 sourcing triage (`skill/phase0_sourcing.md`) needs the same kind of browsing --
one web search, then Thingiverse/Printables/MakerWorld searches, opening the
most-downloaded result on each platform and reading its description, comments, and
license -- but currently does this inline in the main session. It currently points at
Phase 1's search workflow "by reference" for the mechanics, which was a reasonable
shortcut before a Sourcing agent existed, but it means Phase 0's page-reading cost is
paid in the one context Chapter 2 of `ARCHITECTURE.md` says must stay light.

Separately, `prompts/find_parts.md` is dead: not read by `render_prompt.py`, not
referenced by `skill/phase0_sourcing.md`, `ARCHITECTURE.md`, or any `openspec` change. Its
"kernel & language priority" framing and seed-repo list are a plausible discarded first
draft of the same idea, now stale against the actually-maintained corpus in
`documentation/Block_Sources.md` section 2 ("Phase 0 sourcing corpus").

## Goals / Non-Goals

**Goals:**
- Move Phase 0's page-reading search work into an isolated subagent, matching the
  Research agent's pattern exactly (no new orchestration primitive).
- Give Phase 0 its own prompt (`prompts/sourcing.md`) driven off the seed corpus that is
  actually maintained (`documentation/Block_Sources.md` section 2), replacing the stale,
  disconnected `prompts/find_parts.md`.
- Keep the five-rung classification ladder, license rules, and rung-3 user confirmation
  exactly where they are today: main-session judgment calls, not agent output.

**Non-Goals:**
- No change to `BUILD_PLAN.json`'s schema, to the ladder's rung definitions, or to the
  license rules in `skill/phase0_sourcing.md`.
- No change to Phase 1's research workflow or `prompts/research.md` itself (Phase 1 still
  reuses its own search mechanics; only the "by reference" pointer from Phase 0 changes).
- Not building a generic "web search agent" for reuse elsewhere -- scoped to Phase 0
  sourcing, same way the Research agent is scoped to Phase 1 dimension lookup.

## Decisions

**Mirror `render_research()` exactly rather than generalizing a shared helper.**
`render_planning()`, `render_builder()`, `render_audit()`, and `render_research()` are
each a short, independent `fill()` call in `src/render_prompt.py` -- there is no shared
"agent prompt" abstraction to extend, and inventing one for a second, structurally
identical case is speculative. `render_sourcing()` follows the same shape: read a
targets/context input, fill a fixed template, write to `build/sourcing_prompt.txt`, print
`{"out", "chars"}`.

**The agent returns a candidate list, not a rung decision.** The rung ladder involves
judgment the main session already owns (license interpretation, the rung-3 user
confirmation, "does this candidate's discrepancy stay tractable for rung 4"). Keeping
classification in the main session avoids duplicating that judgment inside the agent and
matches the Research agent's boundary: the agent gathers and reports, the checkpoint
owner (main session) decides.

**Candidate schema:** each returned item carries `source` (URL), `platform`
(github/thingiverse/printables/makerworld/other), `kind` (parametric source language, or
`step`/`brep`/`mesh`), `license` (as stated, or `"none stated"`), and `notes` (what was
read: description, comments, linked parametric source). This is enough for the main
session to run the existing ladder without re-opening any page itself.

**`prompts/sourcing.md` draws from `documentation/Block_Sources.md` section 2, not
`prompts/find_parts.md`.** Block_Sources.md is the maintained, dated, rated corpus;
find_parts.md's list has no overlap with it and was never kept current. The new prompt
inlines (or points at) the "Hardware & component archives" and "Finished models by
domain" tables as its seed list, same way `prompts/planning.md` inlines the block
inventory.

**Delete `prompts/find_parts.md` rather than merge it.** Nothing in the repo references
it; merging stale content into the new prompt would just reintroduce the staleness this
change removes.

## Risks / Trade-offs

- **[Risk] Cold-start cost**: a dedicated agent re-pays context setup (reading the seed
  corpus) on every Phase 0 run, where inline search reused whatever the main session
  already had loaded. → Mitigation: this is the same trade-off already accepted for the
  Research agent (see `ARCHITECTURE.md`'s "Known tensions"); Phase 0's quick-pass
  heuristic (custom-dimension requests skip the full ladder) already limits how often the
  full search runs.
- **[Risk] Candidate list underspecifies what the main session needs for a rung-4
  partial-rebuild decision** (freeform vs. axis-aligned discrepancy is currently judged
  from `measure_stl.py` output, not the agent's notes). → Mitigation: rung 4's own
  `measure_stl.py` step is unchanged and still runs in the main session (or a follow-up
  Research-agent-style call) against the *chosen* candidate; the Sourcing agent only
  narrows the candidate set, it does not replace `measure_stl.py`.
- **[Risk] Scope creep into a second "does this generalize" agent-design discussion.** →
  Mitigation: explicitly non-goal'd above; this proposal only touches Phase 0.

## Open Questions

- Should `prompts/sourcing.md` inline the full Block_Sources.md tables, or reference the
  file path and let the agent read it? (Compare: `planning.md` gets the block inventory
  injected via `{{BLOCK_INVENTORY}}`, not a file pointer -- leaning toward the same
  injected-table pattern for consistency, to be confirmed in tasks.)
- Does `documentation/Block_Sources.md` need a stated "last verified" cadence now that a
  prompt depends on it directly, rather than being read ad hoc by a human? Out of scope
  for this change but worth a follow-up TODO item.
