## 1. Classify the existing guidance

- [x] 1.1 Walk `prompts/part.md` lines 7-36 item by item and label each as contract or
      craft, applying design D1's detectability test; record the table in the commit
      message so a later revert can restore one line instead of the section
- [x] 1.2 Confirm each contract item maps to a live detector -- `src/script_lint.py`
      finding types, a `run_cadquery_model.py` typed error, or a named capability -- and
      flag any that maps to nothing for a decision before the rewrite

## 2. Rewrite the part prompt

- [x] 2.1 Replace the 13-item "You should" list in `prompts/part.md` with a compact
      contract block (flat `from blocks import ...`; `result` binding, dict for a
      multi-union part; PARAMETERS block, no magic numbers; `cq_verify` guards at the
      documented risk points) plus one goal-stating paragraph absorbing items 1, 2, 3, 6,
      8-12
- [x] 2.2 Keep the "You should NOT" list enumerated and its six items intact (design D3).
      Header renamed to "Do not:" for parallelism with "Contract rules"; all six items
      unchanged
- [x] 2.3 Add the comment rule -- a comment records a constraint the code cannot show and
      does not narrate the next line -- with the ENGINEERING RATIONALE block and
      `verify_stage` labels named inline as exempt (design D4)
- [x] 2.4 Add the scope-discipline sentence as its own statement, not folded into the
      goal paragraph (design D2): the specified part at the specified scope, no features
      or guards beyond the spec and the required `cq_verify` points
- [x] 2.5 Add the retry-scope sentence: a retry applies a targeted fix for the reported
      error and does not restructure what the error does not implicate
- [x] 2.6 Verify the sections from "Coordinate vocabulary" onward are unchanged except
      for one mechanical cross-reference renumber ("see step 4" -> "contract rule 1" in
      the Available blocks section), which 2.1's renumbering forces. `git diff` shows
      exactly two hunks, so the reference-substitution placeholders and the
      rationale/`cq_verify` contracts are provably untouched

## 3. Align the retry surface

- [x] 3.1 Extend `skill/phase3_build.md` Step 2's "On retry attempts" paragraph with the
      same scope boundary, in place rather than as a new paragraph (design D5)
- [x] 3.2 Confirm the rationale-survives-retries paragraph immediately following it is
      unchanged

## 4. Audit modal language

- [x] 4.1 Grep `prompts/part.md` and `skill/*.md` for `MUST|SHALL|NEVER|ALWAYS|CRITICAL`
      and confirm every surviving hit guards a detectable contract; rewrite any that does
      not as a plain statement. Three hits, all contract, all kept: `part.md:114` (SHALL,
      rationale block present -- detectable on read), `part.md:131` (MUST, check
      references the script's own parameter names -- detectable on read),
      `phase3_build.md:350` (MUST, connectedness answered against a section -- detectable
      via `visual-self-review`'s cited-view requirement). No rewrites needed
- [x] 4.2 Leave `prompts/planning.md`'s two hits alone -- C3 owns that file
      (`git diff` confirms the file is untouched)

## 5. Measure against the C1 baseline

- [x] 5.1 Ran the full 10-case sweep into `evals/runs/c2-de-prescribed/`. First pass hit
      transient Anthropic API errors (500/529) on 3 cases (`two-part-box`, `u-clip`,
      `wall-hook` -- no artifacts produced); regenerated just those three in a second
      `--generate` pass (all three passed), then re-scored the full 10 with no `--generate`.
      Not a repeat of the earlier 3-case smoke subset's cases (that was
      `l-bracket`/`sliding-lid`/`wall-hook`); this is the required full sweep.
- [x] 5.2 Compared `scorecard.md` against `evals/runs/baseline-pre-claude5/scorecard.md`:
      first-shot 0.85 (baseline 0.70, target >= 0.70 -- pass), attempts-to-pass 1.15
      (baseline 1.30, target <= 1.30 -- pass). **Accepted.** Chamfer 3.751mm (baseline
      3.118mm) is reported, not gated. Result recorded in `CLAUDE5_CONVERSION_PLAN.md`
      under C2.
- [x] 5.3 **Amended (design D7).** Metric was not measurable: `prompt_chars` is
      self-reported by the authoring agent (`skill/phase3_build.md` Step 5 asks it to type
      `<len of the rendered step-1 prompt>`), not measured -- `0` in 2 of 6 baseline
      attempts and 1 of 3 subset attempts, every nonzero value a round number (13200,
      13500, 9000, 14000), and the one case with data in both runs (`sliding-lid`) went up
      (13200 -> 14000). D7 now specifies real instrumentation instead of dropping the
      claim -- see 5.3a/5.3b.
- [x] 5.3a Update `skill/phase3_build.md` Step 5 so the Step 1 rendered prompt (both render
      modes) is written to a file before the attempt runs, and `prompt_chars` is computed
      from that file's real character count (`len(pathlib.Path(...).read_text())`) instead
      of typed by the executor. Added a "Measuring the render" note to Step 1 (writes
      `build/<part_id>_prompt_attempt<n>.txt`) and updated Step 5's telemetry field and
      bullet list to require a measured count from that file, never a typed estimate.
- [x] 5.3b Discard existing baseline and c2-subset `prompt_chars` values as unusable
      (self-reported); do not compare them before/after. Only runs recorded after 5.3a
      lands are valid for a token-size comparison. Recorded in design.md D7; no further
      action needed until 5.1/5.2 re-run.
- [x] 5.4 Read one load-bearing case's generated script (`u-clip` or `snap-lid`) and
      confirm the ENGINEERING RATIONALE block survived the comment rule. Checked all
      three subset scripts instead (the subset contains no `u-clip`/`snap-lid`): block
      present in `l_bracket.py:19`, `lid.py:25` (one-line form, correctly, for a
      compression part), `wall_hook.py:28`
- [x] 5.5 Selector-clause fallback not needed; no revert. But "no regression" is too strong:
      a **second full sweep** exists, `evals/runs/c2-prompt-chars/` (run after 5.3a's
      instrumentation landed, prompts otherwise unchanged), scoring first-shot 0.75 and
      attempts-to-pass **1.35** -- passing the first gate, missing the second by 0.05.
      Per-case it disagrees with `c2-de-prescribed` on `snap-lid` (1.00 vs 0.00) and
      `l-bracket` (2 vs 3 attempts).

      Read across all three post-C2 runs: mean first-shot 0.80, mean attempts 1.25, both
      better than baseline's 0.70 / 1.30. But the spread between two runs of the *same*
      configuration (0.85/1.15 vs 0.75/1.35) is as large as the entire measured effect, so
      a single n=1 sweep against a hard threshold cannot separate C2's effect from noise.
      The acceptance stands on the mean; it should not be reported as "first-shot 0.85 vs
      0.70" without the second run beside it.

      Fidelity is flat, not improved: `within_tolerance` is 5/10 at baseline, 3/10 in the
      accepted `c2-de-prescribed`, 5/10 in `c2-prompt-chars`; mean Chamfer 3.118mm ->
      3.751 / 3.449mm. Neither is gated, but neither supports a quality-gain claim.

      Caveat on the comparison: the eval's `claude -p` subprocess runs the *installed*
      skill copy, so both sweeps are assumed to have used the same `prompts/part.md`. That
      was not independently verified.

## 6. Record the outcome

- [x] 6.1 Noted the C2 result and the accepted scorecard path (`evals/runs/c2-de-prescribed/`)
      in `CLAUDE5_CONVERSION_PLAN.md`, including that the token-size claim (design D7)
      still needs a fresh run now that the render-measurement instrumentation is live.
- [x] 6.2 Run `uv run pytest tests/test_plan_validate.py tests/test_script_lint.py` to
      confirm the unchanged enforcement path still passes (99 passed)
