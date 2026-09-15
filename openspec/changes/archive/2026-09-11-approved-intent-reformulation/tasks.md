## 1. Schema and validation

- [x] 1.1 Survey the shortest legitimate `intent` across `evals/cases/*/BUILD_PLAN.json`
      and pick the `minLength` floor (design.md open question); record the chosen value
      and its rationale in a one-line comment beside the constraint.
- [x] 1.2 In `src/build_plan_schema.json`, rewrite `intent`'s `description` to define it
      as the user-approved reformulation Phase 1 writes -- resolved reading, stated
      assumptions, `sketches/` references, no restatement of structured fields -- and
      raise `minLength` from 5 to the value chosen in 1.1.
- [x] 1.3 Add `tests/test_plan_validate.py` cases: a plan with a token `intent` fails; a
      plan with a reformulation-length `intent` passes; a `dimensions.d_mm` of `-1` still
      fails on the existing `exclusiveMinimum` bound; `load.dir: [0, 0, -1]` and a
      negative `interfaces[].position_mm` still validate.
- [x] 1.4 Add the `parameters_unresolved` warning to `src/quality_gate.py`: parse
      `parameters.py` at the project root (same root resolution the existing
      `parameters_missing` check uses) and emit one `warning` finding per name assigned
      `-1`, naming the assignment.
- [x] 1.5 Add gate tests for `parameters_unresolved`: a `-1` assignment warns, a `-2.5`
      assignment does not, no `parameters.py` does not, and `passed` is unaffected either
      way.

## 2. Phase 1: the exit checkpoint

- [x] 2.1 In `skill/phase1_requirements.md`, add the ask-vs-assume rule: rebuild-cost
      ambiguity (part existence, overall shape, joint, fit type) is asked;
      parameter-level ambiguity may be assumed with a concrete value stated in the
      reformulation. Cross-reference the existing "wrong dimension is a parameter edit,
      wrong topology is a rebuild" sentence it generalizes.
- [x] 2.2 Rewrite the "Dimension validation checkpoint" section as the single Phase 1
      exit checkpoint: it presents the reformulation and the table in one message and
      takes one approval. Add `assumed` to the status list. State that approval is not
      accepted while any row reads `-1`/`missing`.
- [x] 2.3 Add the reformulation's content contract to the same section: what it must
      state (intent, confirmed topology, fit types, each assumption with its value,
      `sketches/` paths) and what it must not restate (the dimension table, printer
      fields). Include one worked example.
- [x] 2.4 State that the approved text is written verbatim to `BUILD_PLAN.json`'s
      `intent`, and that `request_log`'s `initial` entry keeps the user's original
      wording unchanged.
- [x] 2.5 Move the sketch-copy rule (copy into `sketches/` as `<slug>-<ts>.<ext>`, record
      the path in the entry's `images`) so it covers an image attached to the opening
      request, and apply it to the `initial` entry in Phase 1. Keep the Phase 3
      correction case working -- update `skill/phase3_build.md` to point at the shared
      rule rather than restating it.
- [x] 2.6 Delete the "Requirements spec write, at approval" section and its
      `phase1/requirements_written` journal line. Leave the `phase1/dimensions_approved`
      line as the checkpoint's milestone.
- [x] 2.7 Update the topology-clarification section to say it stays a separate, earlier
      confirm (it gates which dimensions are looked up) and is not folded into the exit
      checkpoint.

## 3. Phase 2: intent consumed, not authored

- [x] 3.1 In `prompts/planning.md`, change the `intent` instruction: copy the approved
      reformulation verbatim, do not author, paraphrase, or shorten it. Add it to rule 14's
      carry-forward set alongside `request_log`. Keep the rule numbering contiguous per
      the `planning-phase` "rules are uniquely numbered" requirement.
- [x] 3.2 In `prompts/planning.md`, add `intent` to the list of structured fields whose
      content `planning_notes` must not restate.
- [x] 3.3 In `skill/phase2_planning.md`, delete the `REQUIREMENTS.md` amend instruction
      and add the intent carry-forward rule in its place.
- [x] 3.4 Add a planner instruction for the contradiction case: if the decomposition
      would build something the approved `intent` does not describe, revise the
      decomposition -- never edit `intent` to match.

## 4. Phase 3: conformance bar and correction handling

- [x] 4.1 In `skill/phase3_build.md`, re-source the scoped request text for the
      request-conformance bar: approved `intent` plus entries scoped to the part, with
      the `initial` entry as fallback when `intent` is too short to be a reformulation.
      Update both review paths (progressive self-review, Implementation audit).
- [x] 4.2 Add the intent-rewrite rule: when an approved correction changes the design,
      rewrite `intent` to the new reading in the same turn the `request_log` entry is
      appended, deleting superseded wording rather than appending to it. Reference the
      identical `planning_notes` / `part_notes` current-state rule.
- [x] 4.3 Add the no-op case: a correction that changes nothing about the design appends
      to `request_log` and leaves `intent` unchanged.
- [x] 4.4 Add the rule that `sketches/` paths referenced by `intent` are read before
      authoring or re-authoring any part, not only when an entry's `images` names them.

## 5. Phase 4 and skill docs

- [x] 5.1 In `skill/phase4_deliver.md`, remove the `REQUIREMENTS.md` pointer from the
      delivery summary.
- [x] 5.2 In `SKILL.md`, extend the "Request log" section to describe the
      asked/approved pair: `request_log[0]` verbatim and append-only, `intent` the
      approved current state.
- [x] 5.3 Check `CLAUDE.md`, `ARCHITECTURE.md`, `README.md`, and `USE.md` for
      `REQUIREMENTS.md` references and remove any found.
- [x] 5.4 Grep the repository for remaining `REQUIREMENTS.md` mentions outside
      `openspec/changes/archive/` and confirm none remain.

## 6. Eval corpus

- [x] 6.1 Rewrite each `evals/cases/*/BUILD_PLAN.json` `intent` that falls below the new
      floor into a reformulation of that case's `request.md`, in the form Phase 1 would
      produce.
- [x] 6.2 Run `uv run pytest tests/test_eval_corpus.py tests/test_plan_validate.py` and
      confirm every golden validates against the raised floor.
- [x] 6.3 Check for conflicts with the in-flight `import-external-eval-corpus` change on
      the same files; rebase whichever lands second.

## 7. Verification

- [x] 7.1 Run the fast suite: `uv run pytest tests/test_plan_validate.py
      tests/test_eval_corpus.py` plus the gate tests touched in 1.5.
- [x] 7.2 Run `uv run pytest tests/` and confirm no regression from the schema change.
- [x] 7.3 Run `openspec validate approved-intent-reformulation --strict` and confirm the
      change is valid.
- [x] 7.4 Walk one eval case end to end against the updated Phase 1 documentation and
      confirm the exit checkpoint produces a single approval covering both the
      reformulation and the table.
