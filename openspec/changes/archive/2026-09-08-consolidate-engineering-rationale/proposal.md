## Why

The engineering rationale is the one design-critical artefact the pipeline produces that
lives nowhere but a Python comment. Each part script carries its own `ENGINEERING
RATIONALE` block between PARAMETERS and MODEL, so for an N-part model the load reasoning
is spread across N files and no consumer can read it:

- No script reads it. `src/plan_validate.py`, `src/script_lint.py` and
  `src/quality_gate.py` have no notion of it -- a script that silently drops the block,
  or keeps a check whose numbers no longer match its parameters, passes every gate. The
  requirement is enforced only by the prompt asking for it.
- Two authoring paths must each insert it independently. `prompts/part.md` renders the
  requirement on the from-scratch path; the archetype-template path in
  `skill/phase3_build.md` never renders that prompt, so it carries a duplicated copy of
  the trigger rule and the insertion instruction (Step 1.5, "Add the ENGINEERING
  RATIONALE block"). The load-bearing trigger set is prose in both places.
- It does not survive delivery. `README.md` and `REGENERATE.md` are rendered from
  `BUILD_PLAN.json`; the rationale is not in it, so the regeneration prompt hands a fresh
  session the dimensions and the intent but not the load reasoning that produced them --
  exactly the derivation a fresh session cannot re-derive from the numbers.
- Review has to go find it. The `visual-self-review` engineering rows cite "the script's
  ENGINEERING RATIONALE block", which means opening each part script to check a claim the
  plan should already state.

`BUILD_PLAN.json` is where the rest of the per-part design record already lives
(`load`, `part_notes`, `dimensions`, `interfaces`), it is validated by schema, and it is
what Phase 4 renders. The rationale belongs there.

## What Changes

- **New plan field** `parts[].engineering_rationale` in `src/build_plan_schema.json`: an
  object `{load_path, worst_case_stress, check}` for a load-bearing part, or a string for
  the one-line "no load-bearing features (<reason>)" form.
- **The part script no longer carries the block.** `prompts/part.md`'s Engineering
  rationale section becomes a write-back instruction: author the script, then write the
  rationale into the part's plan entry. The script template loses the comment block.
- **One authoring rule for both paths.** Because the write-back is a plan edit rather
  than a script edit, the archetype-template path in `skill/phase3_build.md` follows the
  same rule; its duplicated "Add the ENGINEERING RATIONALE block" instruction is deleted.
- **The trigger set becomes machine-readable.** The load-bearing block/archetype set moves
  into `src/plan_validate.py` as the single canonical list; `prompts/part.md` points at it
  instead of restating it.
- **Plan validation enforces it.** `plan_validate.py` gains
  `check_engineering_rationale`: a part that declares a `load` or uses a load-bearing
  block/archetype must carry the object form; every other part must carry one of the two
  forms. It follows the existing deferred-advisory pattern (`check_deferred_axis_arms`):
  advisory at the Phase 2 run, where no part is authored yet, and an error under
  `--require-rationale` at the Phase 3 pre-export run that already blocks the export.
  This is the first mechanical check the requirement has ever had.
- **Delivery carries it.** `src/regen_prompt.py` renders a rationale column/section, so
  `REGENERATE.md` hands the load reasoning to a fresh session.
- **Review cites the plan.** `visual-self-review` engineering rows cite
  `BUILD_PLAN.json`'s `engineering_rationale` instead of the script comment block.

## Alternatives considered

**Keep the block in the script and mirror it into the plan.** Rejected: two copies of a
number that must stay consistent with the parameters is the failure this change exists to
remove, and nothing would keep the mirror fresh across retries.

**Extract the block from the script at delivery time.** Rejected: it makes a comment a
parsed data format, and it still leaves the archetype path duplicating the insertion rule
and the gates unable to check anything before Phase 4.

**Cost of the choice:** a delivered part script is no longer self-contained -- the load
reasoning for `build/<part>.py` is read from `BUILD_PLAN.json`, which ships in the same
project directory alongside `README.md` and `parameters.py` (which already holds the
sourced measurements the same way). Accepted.

## Impact

- `src/build_plan_schema.json` -- new `parts[].engineering_rationale` field
- `src/plan_validate.py` -- canonical load-bearing trigger set + form-vs-trigger check
- `prompts/part.md` -- Engineering rationale section becomes a plan write-back; script
  skeleton loses the comment block
- `skill/phase3_build.md` -- Step 1.5 rationale-insertion duplicate deleted; write-back
  step added to the part loop; retry rule points at the plan field
- `src/regen_prompt.py` -- rationale rendered into `REGENERATE.md`
- `reference/Visual Review Checklist.md`, `reference/Engineering Design Rules.md` --
  citation source updated
- `tests/test_plan_validate.py`, `tests/test_regen_prompt.py` -- new cases
- `evals/cases/*/BUILD_PLAN.json` -- goldens gain `engineering_rationale` entries
- `openspec/specs/engineering-rationale/`, `part-authoring-guidance/`,
  `visual-self-review/` -- spec deltas
