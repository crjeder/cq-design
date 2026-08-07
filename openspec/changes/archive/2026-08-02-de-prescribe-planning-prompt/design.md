## Context

`CLAUDE5_CONVERSION_PLAN.md` C3 is the planning-side counterpart to C2
(`de-prescribe-part-prompt`, accepted: first-shot 0.70 -> 0.85). C3 is explicitly a
"light touch" phase: the planning prompt is contract-heavy (JSON schema, coordinate
frame, `request_log` append-only rules) and that half stays.

Current state of the two surfaces C3 names:

- `prompts/planning.md` has three ask rules - rule 1 (unverifiable dimension), rule 4
  (unclear fit type), rule 10 (undeterminable load). All three are correct and stay. What
  is missing is the boundary: nothing tells the planner that a coined name, a table-default
  clearance, or plate grouping is *not* a question.
- `skill/phase1_requirements.md` line 119 (**Lookup narration**) tells the model to note
  what it is looking up before and after each lookup. That paragraph already ends by
  admitting the narration reaches nobody, because the lookups moved into a research agent
  with no user channel.

A scan of `SKILL.md`, `skill/phase0_sourcing.md`, `skill/phase2_planning.md`,
`skill/phase4_deliver.md`, and `skill/setup.md` for the other C3-item-2 patterns
(forced progress summaries, "after each step report X", re-check instructions) found
nothing else. The SHALL/MUST/NEVER hits in those files are contract statements
(`request_log` is append-only, `result` must be top-level, Z=0 is the bed) or user
checkpoints, both of which C3 keeps.

## Goals / Non-Goals

**Goals:**

- Bound the planner's ask behavior so 5-series deliberateness does not turn minor
  defaults into user questions, without weakening the three real ask rules.
- Delete the one piece of forced-narration scaffolding on the planning surface, and the
  spec requirement that mandated it.
- Keep the change measurable: same eval corpus, compared against the C2 scorecard.

**Non-Goals:**

- Rewriting the planning prompt's rule list into prose. Unlike `prompts/part.md`'s craft
  advice, these 15 rules are contract (schema fields, frames, id uniqueness) and are
  machine-checked by `plan_validate.py`. De-prescribing them would remove checkable
  contract, not scaffolding.
- Touching `review_policy` semantics, the dimension validation checkpoint, or the Phase 2
  plan summary. Those are intent capture, exempt from the "delete verification" rule
  (C3 item 3).
- `skill/phase3_build.md`. C2 item 6 already handled retry-prompt phrasing there and C8
  owns the autonomy/honesty additions.

## Decisions

**D1. The carve-out goes in `prompts/planning.md`, as its own numbered rule, not inside
rule 4.** The planner's rule list is what the planner agent reads; the carve-out has to be
visible next to the ask rules it bounds. Putting it inside rule 4 (clearance) would scope
it to fit type only, when it also governs names and plate grouping. Alternative considered:
put it in `skill/phase2_planning.md` - rejected, that file is main-session orchestration
and the planner agent never reads it.

**D2. The carve-out is defined by consequence, not by an enumerated list of minor
choices.** "Ask only when different answers change topology, a dimension, or a fit" is a
test the planner can apply to a choice the list never anticipated. The three examples
(coined name, table-default clearance, plate grouping) are illustrations, not the
definition. Enumerating would reproduce exactly the prescriptiveness C2 removed.

**D3. Recording obligation rides on existing machinery.** Decided choices go in
`planning_notes` (already required to hold decomposition reasoning) and coined names still
surface in the Phase 2 summary (already required by rule 2a plus the phase 2 vocabulary
rule). No new field, no new checkpoint - the carve-out reduces questions without reducing
what the user sees before approving the plan.

**D4. The narration paragraph is deleted, not rewritten.** Per the migration guide, the
fix for verification/narration scaffolding is a delete. Rewriting it as "narrate to the
agent's own reasoning" would restate what the model does anyway. The spec requirement is
REMOVED rather than MODIFIED for the same reason: there is no weakened version worth
keeping, and the checkpoint table requirement below it already covers what the user needs.

**D5. Acceptance is the eval corpus plus a clarifying-question count.** The scorecard
metrics (first-shot rate, attempts-to-pass) are insensitive to ask behavior, because the
eval harness runs non-interactively. So the second half of C3's acceptance criterion -
"no increase in clarifying questions on the eval corpus requests" - is measured directly:
count the questions each case's plan stage would raise, before and after, on the same
corpus. A plan that stalls on a question in a non-interactive run shows up as a failed or
degraded case anyway.

## Risks / Trade-offs

- **The carve-out is read too broadly and the planner stops asking about a genuine
  unknown** (e.g. decides a fit type by "reasonable default"). → The carve-out text
  restates the three ask rules as remaining in force, and the spec carries two negative
  scenarios (unverifiable dimension, unclear fit type) that pin them.
- **Fewer questions means more silent decisions the user only catches at the plan
  summary.** → Accepted, and this is the intended trade: the plan summary is a real
  checkpoint with an approval gate, and D3 keeps coined names surfacing there. A wrong
  minor default costs a summary correction; a wrong topology still costs a rebuild, which
  is why topology stays on the ask side.
- **Deleting the narration paragraph loses a debugging trail when a lookup goes wrong.**
  → The research agent still returns its source URL list, which is the part that was ever
  useful; the per-lookup prose was never visible to anyone.
- **Eval noise swamps a small change.** C2's run already hit transient API 500/529s on
  three cases. → Compare against `evals/runs/c2-de-prescribed/` and treat an infra-flagged
  case as a re-run, not a regression, exactly as C2 did.
