## 1. Schema and validation

- [x] 1.1 Add `parts[].engineering_rationale` to `src/build_plan_schema.json`: `oneOf` a
      string (`minLength` enough to force a reason, one-line "no load-bearing features
      (<reason>)" form) or an object with required `load_path`, `worst_case_stress`,
      `check`, `additionalProperties: false`. Describe it as the single home of the part's
      load reasoning, written back in Phase 3.
- [x] 1.2 In `src/plan_validate.py`, add the canonical load-bearing trigger set as a
      module constant (block names from `blocks/inventory.json` + archetype names from
      `templates/archetypes.json`: snap hooks, clips, hooks, brackets, screw bosses, pcb
      standoffs, living hinge, dovetail joints) -- verify every name against those two
      files, do not transcribe the prose list blind.
- [x] 1.3 Add `check_engineering_rationale(plan)` returning findings: field missing;
      triggered part carrying the string form; untriggered part carrying neither form.
      Print it alongside the existing advisory blocks in `main()`.
- [x] 1.4 Add `--require-rationale` to `main()`: when set, `check_engineering_rationale`
      findings are errors and the run exits non-zero.
- [x] 1.5 Add `tests/test_plan_validate.py` cases: object form on a `load` part passes;
      string form on a `load` part is a finding; missing field is advisory without the
      flag and an error with it; string form on an untriggered part passes; a part whose
      `blocks_needed` names a load-bearing block but declares no `load` still triggers.

## 2. Authoring path

- [x] 2.1 Rewrite `prompts/part.md`'s "Engineering rationale" section: the two forms, the
      parameter-name rule, the `reference/Engineering Design Rules.md` pointer, and the
      instruction to write the field into this part's `BUILD_PLAN.json` entry after the
      script is authored. Point at `plan_validate.py`'s trigger constant instead of
      restating the load-bearing list.
- [x] 2.2 Remove the `ENGINEERING RATIONALE` comment block from the script skeleton in
      `prompts/part.md` and from the comment-rule exemption sentence.
- [x] 2.3 In `skill/phase3_build.md` Step 1.5, delete the "Add the ENGINEERING RATIONALE
      block" paragraph -- the write-back is now path-independent.
- [x] 2.4 Add the write-back to the part loop in `skill/phase3_build.md` (same round as
      the existing parameter/placement write-backs), and update the "Rationale survives
      retries" paragraph to say the plan field is re-evaluated and rewritten.
- [x] 2.5 Pass `--require-rationale` on the pre-export `plan_validate.py` run in
      `skill/phase3_build.md`'s **Model export** section.

## 3. Review and delivery

- [x] 3.1 Update `reference/Visual Review Checklist.md`: engineering rows cite the part's
      `engineering_rationale` plan entry, not a script comment block.
- [x] 3.2 Update the header line of `reference/Engineering Design Rules.md` (it points at
      "the ENGINEERING RATIONALE block ... see `prompts/part.md`").
- [x] 3.3 In `src/regen_prompt.py`, render each part's rationale (a section after the
      decomposition table, or a column in it -- pick whichever keeps the table readable
      for a multi-part model) and add a `tests/test_regen_prompt.py` case for both forms.
- [x] 3.4 Check whether `skill/phase4_deliver.md`'s `README.md` step should list the
      rationale; add it only if it does not duplicate what `REGENERATE.md` already
      carries.

## 4. Corpus and docs

- [x] 4.1 Add `engineering_rationale` to every part in `evals/cases/*/BUILD_PLAN.json`
      (object form where the part triggers, string form otherwise) so
      `tests/test_eval_corpus.py` still passes with the pre-export check.
- [x] 4.2 Grep the repo for surviving references to the comment block
      (`documentation/`, `SKILL.md`, `openspec/specs/`) and update the live ones; leave
      `openspec/changes/archive/` and `documentation/DONE.md` untouched as history.
- [x] 4.3 Run `uv run pytest tests/test_plan_validate.py tests/test_regen_prompt.py
      tests/test_eval_corpus.py`, then the full suite.
- [x] 4.4 Promote the TODO.md item into "V1 defects" with a pointer to this change
      (done when this change was written).
