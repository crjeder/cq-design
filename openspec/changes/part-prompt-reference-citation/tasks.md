## 1. Template change

- [ ] 1.1 Edit `prompts/part.md`: keep `{{CQ_REFERENCE}}` / `{{FDM_GUIDELINES}}`
  placeholders, add the mode rule comment; draft the inline citation block wording
  (documents by path, FDM section-name list, emboss gating)
- [ ] 1.2 Update the SKILL.md Phase 3 Step 1 substitution table: mode-keyed values
  (inline -> citation block / section-name list; cold -> full contents as before)
- [ ] 1.3 Add the precondition rule to SKILL.md: inline citation only after the
  Phase 3 setup reads; re-read on resumed/compacted sessions before first render

## 2. Consistency

- [ ] 2.1 Verify the quality gate's `claude -p` fix prompt path still renders full
  substitution (no code change expected; confirm wording in SKILL.md quality-gate
  section)
- [ ] 2.2 Confirm retry-prompt instructions in SKILL.md inherit the mode (inline
  retries cite)
- [ ] 2.3 Grep SKILL.md/prompts for stale references to unconditional full
  substitution and update

## 3. Measure

- [ ] 3.1 Record a before/after eval-corpus run (`evals/run_evals.py`) with
  scorecards; guardrail: first-shot pass rate and attempts-to-pass not regressed;
  target: prompt-size per attempt in `build/attempts.jsonl` drops by roughly the
  reference payload
- [ ] 3.2 Note the scorecard comparison in the change (or PR) description
