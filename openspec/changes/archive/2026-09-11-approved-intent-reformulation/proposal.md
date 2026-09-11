## Why

Phase 1 ends without the user ever approving a statement of what will be built. The
user's raw ask ("a stand for my laptop") is preserved verbatim in `request_log[0]`, and
the dimension table is approved, but the resolved reading of the request -- topology,
fit, assumptions, which artefacts it is based on -- is never read back for confirmation.
`intent` is the one required, structured, downstream-read field that could carry it, yet
today the Phase 2 planner authors it from scratch and nobody checks it. The consequence
lands in Phase 3: the request-conformance acceptance bar measures every render against
`request_log`'s `initial` entry -- the vague ask -- which is a weak bar precisely where a
strong one is cheapest to apply.

`REQUIREMENTS.md` was introduced to hold this resolved state, but five of its six
sections restate structured fields that already exist (`parameters.py`,
`parts[].dimensions`, `interfaces[]`, `printer`/`material`/`nozzle_mm`), no script or
schema reads it, and it is skippable. It duplicates without binding.

## What Changes

- Phase 1 gains a single **exit checkpoint** that presents the restated request and the
  dimension table together, for one approval. The topology-clarification confirm stays
  where it is (it gates which dimensions are even looked up); the separate
  intent-approval round is never introduced.
- The approved restatement is written verbatim into `BUILD_PLAN.json`'s `intent`. It
  reformulates the ask in resolved terms, names every assumption made, and references
  every user-supplied sketch/photo by its `sketches/` path.
- `intent` becomes **current-state**: rewritten on each approved correction, matching the
  rule already binding `planning_notes` and `part_notes`. `request_log` remains the
  append-only history. Together they are the "user asked for" / "user approved" pair.
- Phase 2 plans against the approved `intent` and carries it forward across a re-plan
  instead of authoring it. Phase 3's request-conformance bar measures renders against
  `intent` plus scoped `request_log` entries, rather than the `initial` entry.
- Phase 1 must resolve every ambiguity that would cost a rebuild (a part's existence, a
  joint, a fit type) by asking. A parameter-level unknown may instead be **assumed** with
  a concrete value, stated in the approved text -- changing a number later is cheap. No
  dimension may leave Phase 1 as `-1`.
- The dimension table gains an `assumed` status value, so a deliberately-picked
  starting value is distinguishable from `missing`.
- The `-1` placeholder is caught where it can actually survive. The plan schema already
  rejects `-1` on every size-valued field via `exclusiveMinimum: 0`, and its remaining
  unbounded numeric fields are signed by design (positions, directions, translations,
  angles, ranges) where `-1` is legitimate -- so no blanket plan-level `-1` rule is added.
  Instead the quality gate warns when `parameters.py` assigns `-1`, which is the one file
  that records an approved `missing` row verbatim. `intent` gains a schema length floor as
  the backstop for the reformulation itself.
- The Phase 1 sketch-copy rule (copy attachment into `sketches/`, record the path in the
  entry's `images`) applies to the `initial` entry, not only to mid-build corrections.
- **BREAKING**: `REQUIREMENTS.md` is no longer written, and the `requirements-spec-capture`
  capability is removed. Existing projects that carry the file keep it as an inert
  artifact; nothing reads it today.
- **BREAKING**: `intent`'s schema `minLength` rises from 5, which invalidates any existing
  plan carrying a token intent -- including eval-corpus goldens, which are updated in this
  change.

## Capabilities

### New Capabilities
- `approved-intent`: the user-approved reformulation of the request written into
  `BUILD_PLAN.json`'s `intent` at the Phase 1 exit checkpoint -- what it must contain
  (resolved reading, stated assumptions, artefact references), the ask-vs-assume rule
  that decides when Phase 1 may proceed, and the current-state maintenance rule that
  rewrites it on each approved correction while `request_log` keeps the history.

### Modified Capabilities
- `dimension-validation-checkpoint`: the checkpoint becomes the single Phase 1 exit gate,
  approving the restated intent alongside the table in one round; `assumed` joins the
  status vocabulary; no row may remain `missing`/`-1` at approval.
- `request-relative-acceptance`: the second acceptance bar reads the approved `intent`
  plus scoped `request_log` entries instead of the `initial` entry; the skip condition
  changes from "no `request_log`" to "no approved intent".
- `request-log`: the sketch-copy-and-reference rule extends to the `initial` entry
  written in Phase 1, so an image attached to the opening request is captured.
- `planning-phase`: the planner consumes the approved `intent` rather than authoring it,
  carries it forward unchanged across a re-plan, and no longer amends `REQUIREMENTS.md`;
  plan validation additionally rejects a below-threshold `intent`.
- `parameters-provenance-check`: the gate warns when `parameters.py` assigns the `-1`
  unresolved-dimension placeholder.
- `requirements-spec-capture`: **removed in full** -- Phase 1 no longer writes
  `REQUIREMENTS.md`, Phase 2 no longer amends it, Phase 4 no longer points at it, and the
  `phase1/requirements_written` journal line is retired.

## Impact

- `skill/phase1_requirements.md` -- merged exit checkpoint, ask-vs-assume rule, initial-entry
  sketch handling, `REQUIREMENTS.md` section deleted
- `skill/phase2_planning.md`, `prompts/planning.md` -- intent consumed not authored;
  `REQUIREMENTS.md` amend step deleted
- `skill/phase3_build.md` -- conformance bar sourced from `intent`; intent rewrite on an
  approved correction
- `skill/phase4_deliver.md` -- `REQUIREMENTS.md` pointer removed
- `src/build_plan_schema.json` -- `intent` description and `minLength`
- `src/quality_gate.py` -- `parameters_unresolved` warning
- `SKILL.md` -- Request log section gains the intent pairing
- `tests/test_plan_validate.py` -- intent-length cases
- `evals/cases/*/BUILD_PLAN.json` -- goldens updated to satisfy the new `intent` floor
  (collides with the in-flight `import-external-eval-corpus` change on the same corpus)
- `openspec/specs/requirements-spec-capture/` -- capability removed
