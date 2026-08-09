## 1. Baseline and evidence

- [x] 1.1 Record pre-change byte size of both reference documents and compute the 65% targets
- [x] 1.2 Aggregate error types from `evals/runs/*/*/build/attempts.jsonl` and record the counts in design.md's Context if they have shifted
- [x] 1.3 Record baseline mean cold-render `prompt_chars` from `evals/runs/c2-prompt-chars` (cold = the large-value cluster, inline renders excluded)
- [x] 1.4 Grep `prompts/`, `skill/`, `SKILL.md` for citations of these two documents by *section* name (design D-risk 3 expects none; confirm)

## 2. Condense CadQuery Anti-Patterns.md

- [x] 2.1 Retain every Tier 1 and Tier 2 entry; compress each wrong/right code pair to one line per side
- [x] 2.2 Retain the four Tier 3 API-mechanics entries, cutting surrounding prose
- [x] 2.3 Remove the intro/framing prose that restates general CAD or Python fundamentals
- [x] 2.4 Verify the file is at or under 65% of its pre-change size (8,527 bytes); if not, note in design.md Open Questions which entry would have to go and leave it in place

## 3. Condense CadQuery Pattern Reference.md

- [x] 3.1 Delete the Table of Contents (pure token cost in a pasted document)
- [x] 3.2 Retain and tighten the signature/semantics sections: Workplane Naming, Face & Edge Selectors (all subsections), Center Selection, Common Gotchas, Workplane Context Stacking
- [x] 3.3 Cut or fold the recallable sections: Basic Shapes, BRep Vocabulary, Sketch API narration, Array Methods, Accessing Objects & Debugging
- [x] 3.4 Cross-check remaining worked examples against `templates/*.py`; drop any whose idiom an archetype template already demonstrates
- [x] 3.5 Verify the file is at or under 65% of its pre-change size (15,408 bytes)

## 4. Record decisions

- [x] 4.1 Append a per-section retain/cut table with its justification (signature / failure signature / table / contract / observed error type) to design.md, as the spec requires

## 5. Measure

- [x] 5.1 Run `uv run python evals/run_evals.py --generate` over the canonical corpus into `evals/runs/c5-condensed/` (9/10 cases scored -- `wall-hook` hit a Claude session usage limit twice in a row and never generated; see design.md)
- [x] 5.2 Compare first-shot rate and attempts-to-pass against `evals/runs/c4-review-collapse/scorecard.json`
- [x] 5.3 Compute mean cold-render `prompt_chars` for the new run and compare against the 1.3 baseline
- [x] 5.4 If first-shot rate or attempts-to-pass regressed, narrow the cuts (restore the most load-bearing removed sections) and re-run before proceeding (not triggered -- no regression on the matched 9-case subset)

## 6. Land

- [x] 6.1 Add a C5 result block to `CLAUDE5_CONVERSION_PLAN.md` in the same format as the C2 block, stating both metrics honestly including run-to-run spread
- [x] 6.2 Update `IMPROVEMENT_PLAN.md` item 14 status
- [x] 6.3 Run `uv run pytest tests/` to confirm nothing referenced these documents programmatically
