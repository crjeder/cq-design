# Sub-agent pipeline

## Why

The pipeline currently runs entirely inline in one session, which has three
compounding costs:

1. **Context pressure.** Preview PNGs from up to 3 attempts x N parts, web page
   snapshots from dimension lookups, and the full reference corpus all
   accumulate in one context window and never leave. Long multi-part builds
   degrade or hit summarization mid-build.
2. **Self-review bias.** The Phase 3 Step 4 visual self-review is the author
   grading its own homework - `feature_presence_check.py` exists precisely as a
   deterministic backstop for that weakness. A fresh-context auditor that never
   saw the script is the strong version of the check.
3. **No model routing.** Planning (where a topology error costs a full rebuild)
   and part authoring (code generation against a strong prompt) run on whatever
   model the session happens to use. `telemetry.py`'s `model` field is
   hardcoded to `"inline"` - the measurement slot for routing exists but is
   unused.

The architecture is drafted in `ARCHITECTURE.md` (agent roster, boundaries,
tensions).

## What Changes

- **Phase 3 part loop routes autonomous parts through builder sub-agents**: one
  Agent-tool call per part, prompt = the already-self-contained rendered
  `prompts/part.md`, internal write/lint/validate/render/self-check loop (max 3
  attempts, draft and refine in ONE agent). Returns verdict + bbox + preview
  paths + telemetry rows; images stay in the agent. Progressive parts (existing
  complexity gate, or user override) stay inline in the main session.
- **Escalation resumes the same agent**: `blocked` after 3 attempts -> main
  asks the user for a hint -> the same builder is resumed with the hint,
  attempt context intact.
- **Implementation auditor agent** replaces the author-side visual review as
  the acceptance bar: fresh context, receives plan part entries + preview/
  section PNGs but never the scripts, answers the Visual Review Checklist with
  cited views. The builder keeps only a light self-check for obvious misses.
- **Planner agent** runs Phase 2 plan generation with a per-call strong-model
  override; `plan_validate.py` gating and user approval stay in main.
- **Research agent** runs the Phase 1 dimension-lookup workflow (web search,
  spec pages, community models, `measure_stl.py`) and returns only the
  dimension validation table + sources; requirements Q&A and the approval
  checkpoint stay in main.
- **Telemetry `model` field records the actual model** used per attempt instead
  of `"inline"`.
- **Adoption is eval-gated**: before/after scorecards from `evals/run_evals.py`
  (first-shot rate, attempts-to-pass, cost per accepted part, Chamfer
  distance); a worse scorecard means fix or revert.

## Capabilities

### New Capabilities

- `subagent-orchestration`: which pipeline roles run as sub-agents, what
  crosses each agent boundary (in and out), which interactions must stay in the
  main session, and how escalation/resume works.

### Modified Capabilities

(none yet in main specs - the part-loop and planning behavior contracts are
unchanged; what changes is where they execute. `skill-doc-structure` from
`split-skill-md` is a prerequisite, not modified: its per-phase files become
the per-agent instruction sources.)

## Impact

- `SKILL.md` / `skill/phase*.md` (after `split-skill-md` lands): Phase 1-3
  orchestration text gains agent routing, return contracts, and the resume
  path. No `src/` script behavior changes.
- `src/telemetry.py` usage: `model` field gets real values (helper itself
  already accepts any string).
- `ARCHITECTURE.md`: updated (done alongside this proposal).
- Sequencing: depends on `split-skill-md`.
- Risk surface: cold-start token cost per builder (references re-read N times),
  interface drift between isolated builders of mating parts, telemetry append
  collisions if builders run in parallel. All three are named in
  `ARCHITECTURE.md` and covered by the eval gate or an explicit task.
