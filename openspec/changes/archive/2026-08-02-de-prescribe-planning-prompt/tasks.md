## 1. Baseline

- [x] 1.1 Confirm `evals/runs/c2-de-prescribed/scorecard.json` is present and is the most
      recent accepted run; note its first-shot rate and attempts-to-pass as the comparison
      baseline (C2 result: 0.85 / 1.15).
- [x] 1.2 Record the current clarifying-question count per eval case in
      `evals/cases/*/request.md` terms: for each case, list which of the three ask rules
      (unverifiable dimension, unclear fit type, undeterminable load) its request would
      trigger today. This is the "before" side of C3's second acceptance criterion; a
      short note in the change dir is enough, no tooling.

## 2. Minor-decision carve-out (`prompts/planning.md`)

- [x] 2.1 Add a new numbered rule to the Rules section of `prompts/planning.md`, placed
      after rule 4 (clearance by fit type), stating the carve-out by consequence per
      design D2: minor choices - a coined part or interface name, a clearance the fit-type
      table already supplies for the stated fit, plate grouping - are decided and recorded
      in `planning_notes`; ask only when different answers change the topology, a
      dimension, or a fit.
- [x] 2.2 In the same rule, restate that rules 1 (unverifiable dimension), 4 (unclear fit
      type), and 10 (undeterminable load) remain questions for the user, so the carve-out
      cannot be read as overriding them.
- [x] 2.3 Do not renumber the existing rules if the file uses letter suffixes for
      insertions (`2a`, `3a`, `11a`); follow that convention so downstream references
      ("rule 3a", "rule 12" in `skill/phase2_planning.md` and
      `openspec/specs/planning-phase/spec.md`) stay valid.
- [x] 2.4 Grep the repo for references to planning-prompt rule numbers and confirm none
      broke: `grep -rn "rule [0-9]" skill/ SKILL.md openspec/specs/ prompts/`.

## 3. Delete the narration scaffolding

- [x] 3.1 Delete the **Lookup narration** paragraph from
      `skill/phase1_requirements.md` (currently the paragraph beginning "Lookup
      narration:" between the Playwright tool-usage section and the Dimension validation
      checkpoint heading). Leave the research agent's return contract (the validation
      table plus the source URL list) untouched.
- [x] 3.2 Verify nothing else in `skill/` or `SKILL.md` points at that paragraph:
      `grep -rni "narration\|announce" skill/ SKILL.md prompts/`.

## 4. Mirror to the installed skill copy

- [x] 4.1 Copy the edited `prompts/planning.md` and `skill/phase1_requirements.md` into
      `~/.claude/skills/cq-design/`. The eval harness's `claude -p` subprocess runs the
      installed copy, not the repo, so an unmirrored edit is not measured (this is what
      cost C2 its `prompt_chars` measurement).
- [x] 4.2 Diff the two copies to confirm they match on both files.

## 5. Validate and measure

- [x] 5.1 `openspec validate de-prescribe-planning-prompt --strict`.
- [x] 5.2 `uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` - the
      corpus plans must still validate (no schema or rule-number breakage).
- [x] 5.3 Run the eval corpus: `uv run python evals/run_evals.py --generate --run-dir
      evals/runs/c3-planning/`, then score it. Compare first-shot rate and
      attempts-to-pass against `evals/runs/c2-de-prescribed/`; treat any case that hit a
      transient API 500/529 as a re-run, not a regression. Two consecutive runs were
      truncated by the account's session usage limit (6 then 3 of 10 cases missing);
      accepted the second run's 7/10 partial result per user decision rather than
      retrying a third time.
- [x] 5.4 Redo the 1.2 count on the new run and confirm the number of clarifying questions
      did not increase. `--generate` runs are non-interactive; grepped completed cases'
      `README.md` for any surfaced ambiguity/clarification text - none found, consistent
      with the pre-run table (0/10 genuine rule 1/4/10 triggers on this corpus).
- [x] 5.5 If first-shot rate or cost per accepted part regressed, revert both edits per
      the conversion plan's standing rule and record why in the change's proposal. No
      revert: of 7 completed cases, 6 passed first-shot; `l-bracket`'s first-shot-0 matches
      its already-flaky C2 baseline (chamfer improved 12.75mm -> 7.9mm, not worse);
      `adapter-ring`'s single failed attempt was `dimension_mismatch`, a Phase 3
      part-authoring error unrelated to this change's Phase 1/2 scope.

## 6. Record the result

- [x] 6.1 Append a **Result** paragraph to `CLAUDE5_CONVERSION_PLAN.md` section C3, in the
      same shape as C2's: change name, run dir, the two scorecard numbers vs. baseline,
      the clarifying-question comparison, and anything the run failed to measure.
- [x] 6.2 Archive the change: `openspec archive de-prescribe-planning-prompt`, which
      removes the "Dimension lookups are announced before they start" requirement from
      `openspec/specs/dimension-validation-checkpoint/spec.md` and creates
      `openspec/specs/planning-decision-scope/spec.md`.
