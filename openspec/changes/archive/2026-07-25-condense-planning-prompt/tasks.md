## 1. Prep

- [x] 1.1 Re-run `grep -rn "rule \d\+" --include=*.md .` (already run once during
      proposal drafting) and record every file/line that cites a
      `prompts/planning.md` rule number, as the baseline to re-check against after
      the rewrite (`skill/phase2_planning.md`, `skill/phase3_build.md`, `TODO.md`).
- [x] 1.2 Build the rule-by-rule coverage checklist from the current
      `prompts/planning.md` (rules 1-13, plus the duplicate 14/14/15 tail):
      one line per distinct SHALL/MUST obligation, to check off as each lands in
      the condensed text. Keep this as a scratch note (commit message / PR
      description), not a repo file.

## 2. Rewrite prompts/planning.md

- [x] 2.1 Condense rules 1-13: convert narrative paragraphs into a lead SHALL
      sentence plus bullets/tables, keeping the 8-step proprietary-interface
      lookup (rule 1) and the clearance table (rule 4) as-is in structure, and
      keeping the explicit interface-type examples in rule 5
      (`face_mount`/`snap_hook`/`joint_axis`/`union`) inline. Rule numbers and
      sub-letters (2a, 3a, 11a) stay unchanged.
- [x] 2.2 Merge the two `request_log` statements (current rules 14 and 15) into
      one rule 14.
- [x] 2.3 Renumber the provenance rule (currently the second, colliding `14.`)
      to `15`.
- [x] 2.4 Tick off every item on the coverage checklist from 1.2 against the new
      text; for any unticked item, either fold it in or explicitly note in the
      commit description why it's no longer needed.
- [x] 2.5 Leave the output schema JSON block, the `{{BLOCK_INVENTORY}}` /
      `{{ARCHETYPE_INDEX}}` / `{{PRINTER_PROFILE}}` / `{{FDM_GUIDELINES}}` /
      `{{USER_REQUEST}}` placeholders, and the coordinate-vocabulary section
      untouched.

## 3. Verify no stale cross-references

- [x] 3.1 Re-run the `rule \d+` grep from 1.1 and diff against the baseline;
      confirm every hit for `prompts/planning.md` rule numbers
      (`skill/phase2_planning.md`, `skill/phase3_build.md`) still names a rule
      whose content matches what's at that number in the rewritten file.
- [x] 3.2 If any cross-reference now points at the wrong rule (renumbering
      assumption in design.md turned out wrong), update that reference in place.
      (No stale references found -- nothing to update.)

## 4. Validate

- [x] 4.1 `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py`
      (schema/corpus sanity -- unaffected by wording, cheap confirmation nothing
      else broke). 102 passed.
- [ ] 4.2 Optional: spot-check with `evals/run_evals.py --generate` on one
      multi-rule eval case (interfaces + load + archetype) before/after the
      rewrite to catch a plan-quality regression the coverage checklist missed.
      (Skipped -- requires live LLM calls; not run without explicit request.)

## 5. Close out

- [x] 5.1 Update `TODO.md`'s "optimize prompts" item: mark the
      "the planning.md template itself (13 verbose rules) could be condensed"
      sub-item done, in the same style as the existing "Pass 1 done" note.
