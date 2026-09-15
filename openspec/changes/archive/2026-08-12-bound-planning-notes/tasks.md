## 1. Rewrite the charter in prompts/planning.md

- [x] 1.1 Replace the charter sentence at `prompts/planning.md:39` ("Before committing to
      any dimension values, populate `planning_notes` with your reasoning: why you chose
      this decomposition, how you derived dimensions, which sources you checked, and any
      design trade-offs.") with the three-category inclusion rule from design D2/D3:
      (a) decisions against something with the reason, including deliberately omitted
      optional fields and their compensating measures; (b) invariants binding more than
      one part; (c) the assembly procedure and the non-printed hardware it consumes.
      State explicitly that content outside the three categories does not belong there.
- [x] 1.2 Keep the dimension-research instruction that the old sentence carried: the
      "record sources / unverifiable dimension" behavior currently leaning on that
      sentence is covered by rules 1 and 4 -- verify by reading them, and if a source-
      recording obligation exists nowhere else, keep it as category (a) content
      ("dimension X could not be verified, placeholder -1, asked user") rather than
      dropping it silently.
- [x] 1.3 Add the no-prose-restatement rule (design D4): anything expressed by
      `placement`, `pose_intent`, `load`, `dimensions`, `blocks_needed`, `interfaces`,
      `intent`, or `optimize_for` is not narrated in `planning_notes`; the structured
      field is the single source. Include the category (b) carve-out: a cross-part
      consequence of a structured value stays admissible. Fold rule 8a's
      `placement`-specific ban into this general rule, or cross-reference it, without
      renumbering either.
- [x] 1.4 Extend rule 14 with the re-plan consumption clause (design D5): on a re-plan
      the agent reads the existing `planning_notes` before re-deciding, does not silently
      re-litigate a decision recorded there, and rewrites the field to the current state
      -- contrasted with `request_log`, which is carried forward entry by entry and never
      edited.
- [x] 1.5 Verify no rule was renumbered: `grep -n "rule [0-9]" skill/phase2_planning.md
      skill/phase3_build.md prompts/part.md` and confirm every cited number still points
      at the same subject matter.

## 2. Propagate to the schema and skill docs

- [x] 2.1 Update the `planning_notes` description in `src/build_plan_schema.json` to name
      the three categories alongside the existing current-state-only sentence
      (design D6). Description text only -- do not add a property, type, or constraint.
- [x] 2.2 Update `skill/phase2_planning.md:67-72` (the passage contrasting
      `planning_notes` with `parameters.py` and the part `PARAMETERS` block) so its
      one-line characterization matches the inclusion rule instead of "explains
      reasoning".
- [x] 2.3 Grep the remaining `planning_notes` mentions in `skill/phase0_sourcing.md`,
      `skill/phase1_requirements.md`, and `skill/phase2_planning.md` and confirm each
      still fits a category or is a provenance mention. Provenance stays put for this
      change (the move to a structured field is a filed post-V1.0 item); note any mention
      that fits no category in the change's notes rather than editing it here.

## 3. Verify

- [x] 3.1 Run `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` and
      confirm both pass -- the schema description edit must not change any plan's
      validity.
- [x] 3.2 Re-read the audited C5 `planning_notes` (recorded in `TODO.md` under the
      rationale-audit item) against the new rule and confirm the three retained
      categories are admitted and the four restatement/changelog classes are excluded.
- [ ] 3.3 Update `openspec/specs/planning-phase/spec.md` from the delta spec, or leave it
      to `/opsx:archive`, per the project's usual archive flow.
- [x] 3.4 Mark the rationale-audit item at `TODO.md:221` done, referencing this change,
      and confirm the three post-V1.0 follow-ups (provenance move, structured
      decisions-against entries, bill of non-printed materials) remain listed.
