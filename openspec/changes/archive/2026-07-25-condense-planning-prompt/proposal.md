## Why

`prompts/planning.md` (the Phase 1/2 planning prompt) has grown to 13 numbered rules
(~330 lines) of mostly prose, injected verbatim into every planning-phase LLM call.
`TODO.md` already tracks "prompts are growing too long" as an open item, with this
file named as the next target after the `emboss_text.md` pass. The rules also contain
an accidental duplicate: rule 14 appears twice (once for `request_log`, once for
provenance) and rule 15 restates the `request_log` rule from rule 14 a second time.
Condensing the prompt reduces token cost on every planning call without changing what
the planner is required to produce.

## What Changes

- Rewrite `prompts/planning.md`'s rule block into denser prose/tables, preserving every
  currently-mandated behavior (dimension research and the proprietary-interface lookup
  sequence, decomposition, user-noun naming, block/archetype selection, the clearance
  table, declarative placement/`joints`/`unions` assembly, `kinematics`, per-part `load`,
  `optimize_for`, `review_policy`, the `shadow_gap` seam proposal, the `cq_gears`
  pointer, `request_log`, and found-source provenance).
- Remove the duplicated rule 14/15 content (the two `request_log` statements and the
  provenance rule sharing the `14.` label) by merging into one statement each.
- Re-derive rule numbering as a result of the merge and update every cross-reference to
  a `prompts/planning.md` rule number elsewhere in the repo (`skill/phase2_planning.md`,
  `skill/phase3_build.md`) so they still point at the correct rule after renumbering.
- No change to the required output schema, the `{{...}}` placeholders, or any field the
  LLM must emit -- this is a wording/structure change to the prompt text, not a
  behavior change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `planning-phase`: adds one new requirement -- `prompts/planning.md`'s Rules section
  must assign each rule a unique identifier, so that a cross-reference to a specific
  rule number (from `skill/phase2_planning.md`, `skill/phase3_build.md`, or elsewhere)
  unambiguously resolves to one rule. This is the requirement the current duplicate
  `14.`/`14.` pair violates today; everything else about planner behavior and the
  `BUILD_PLAN.json` contract is unchanged.

## Impact

- `prompts/planning.md` -- rewritten rule block (Why/What above).
- `skill/phase2_planning.md`, `skill/phase3_build.md` -- rule-number cross-references
  updated to match the renumbered rules.
- `TODO.md` -- mark the "condense planning.md template" sub-item done.
- No schema, code, or test changes expected (`test_plan_validate.py` and
  `test_eval_corpus.py` validate `BUILD_PLAN.json` structure, not prompt wording).
- Regression risk is qualitative: a condensed prompt could omit a nuance an LLM
  currently relies on. Mitigate by keeping a rule-by-rule coverage checklist during the
  rewrite (see `design.md`) and spot-checking with the eval harness
  (`evals/run_evals.py --generate`) before/after on at least one case that exercises
  most rules (e.g. a multi-part case with interfaces, load, and archetypes).
