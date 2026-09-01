## Why

Phase 1 (`skill/phase1_requirements.md`) already resolves intent, topology ambiguity,
fit types, DFM constraints, and sourced dimensions -- but the only persisted trace of
that work is scattered: `parameters.py` captures raw sourced numbers, `build/journal.md`
gets one-line milestones, and the approved dimension table lives only in the chat
transcript. There is no single reviewable document a user (or a later session) can read
to see *why* the plan looks the way it does without replaying the conversation. This is
the same gap OpenSpec itself closes for feature intent: an intent gets clarified into a
written spec before a plan is generated from it. `BUILD_PLAN.json` plays the "plan"
role already; nothing plays the "spec" role.

## What Changes

- Add a "Requirements spec write, at approval" step to `skill/phase1_requirements.md`,
  a sibling of the existing "Provenance write, at approval" section, run at the same
  checkpoint (same turn, immediately after `parameters.py` is written).
- The step writes `REQUIREMENTS.md` at the project root: intent, confirmed topology
  reading, the dimension table, fit requirements per interface, resolved DFM
  constraints (noting profile-default vs. stated one-time exception), and any open
  questions/assumptions left unresolved.
- Skipped only when Phase 1 resolved nothing beyond bare user-stated numbers already
  inline in the request (no topology ambiguity, no dimension lookups, no stated fit
  type) -- the same skip condition already used for the dimension-validation
  checkpoint, widened to also cover fit type.
- Phase 2 amends the same file in place if planning introduces or changes a
  requirement; it is never regenerated from scratch.
- This is a documentation-only change to the skill's Phase 1 prompt -- no schema, no
  new script, no change to `BUILD_PLAN.json` or its validation.

## Capabilities

### New Capabilities
- `requirements-spec-capture`: Phase 1 writes a human-readable `REQUIREMENTS.md`
  capturing intent, topology, dimensions, fit, and constraints, as the durable spec
  underlying the generated plan.

### Modified Capabilities
(none -- `dimension-validation-checkpoint` and `parameters-provenance-check` are
unchanged; this adds a parallel write, it does not alter either)

## Impact

- `skill/phase1_requirements.md`: one new section, sibling to "Provenance write, at
  approval".
- No changes to `src/`, no new CLI tool, no schema change.
- Follow-up (not in scope here, parallel to how `parameters-provenance-check` followed
  the original `parameters.py` convention by a separate change): a possible advisory
  quality-gate stage that warns when `REQUIREMENTS.md` is missing after
  `build/journal.md` records `phase1/requirements_written` was expected. Deferred --
  see design.md.
