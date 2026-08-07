## Why

The 5-series migration guidance (see `CLAUDE5_CONVERSION_PLAN.md` phase C3) has two
consequences for the planning surface: 5-series models are more deliberate about asking,
so an "ask the user" rule set with no carve-out floods the user with questions about
choices that do not change the design; and forced-narration scaffolding ("announce each
lookup before you run it") is scaffolding the model no longer needs. `prompts/planning.md`
and `skill/phase1_requirements.md` still carry both. C2 already did this for the part
surface (`de-prescribe-part-prompt`); this is the planning-side counterpart.

The narration rule is additionally stale: Phase 1's dimension lookups now run inside a
research agent with no user channel, so a rule saying "the skill outputs a message before
each lookup" cannot be satisfied as written and the phase doc already contradicts it.

## What Changes

- `prompts/planning.md`: add a minor-decision carve-out alongside the existing ask rules
  (dimension unknowns rule 1, fit type rule 4, load rule 10). Minor choices - a coined
  part name, a default clearance already in the fit table, plate grouping - are decided by
  the planner and recorded in `planning_notes`; asking is reserved for a choice that
  changes topology, a dimension, or a fit.
- `skill/phase1_requirements.md`: delete the **Lookup narration** paragraph. It is forced
  narration inside an agent that has no user channel; the user-visible artifact is the
  Dimension validation checkpoint table, which stays.
- Everything else on this surface is deliberately unchanged: the ask rules themselves, the
  dimension validation checkpoint, the Phase 2 plan summary and approval, `review_policy`
  semantics, and every contract-level SHALL/MUST in the planning prompt (schema, coordinate
  frame, `request_log` append-only rules). A scan of `SKILL.md` and
  `skill/phase{0,2,4}*.md` found no other forced-narration or re-check scaffolding: the
  Phase 2 summary and Phase 4 report are user checkpoints and deliverables, not model
  self-verification.

## Capabilities

### New Capabilities
- `planning-decision-scope`: when the planner asks the user versus decides and records -
  the minor-decision carve-out and its recording obligation in `planning_notes`.

### Modified Capabilities
- `dimension-validation-checkpoint`: removes the "Dimension lookups are announced before
  they start" requirement. The checkpoint table requirement and the correction-handling
  requirement are unchanged.

## Impact

- `prompts/planning.md` (one added rule)
- `skill/phase1_requirements.md` (one deleted paragraph)
- `openspec/specs/dimension-validation-checkpoint/spec.md` (one requirement removed on
  archive)
- No Python changes. No schema changes. Acceptance is `evals/run_evals.py` against the
  post-C2 scorecard (`evals/runs/c2-de-prescribed/`), plus a check that the eval corpus
  requests do not produce more clarifying questions than before.
