## Context

The part loop renders `prompts/part.md` per part per attempt. Today the template
carries `{{CQ_REFERENCE}}` (pattern reference + anti-patterns, plus emboss gotchas
for text parts) and `{{FDM_GUIDELINES}}` (tag-filtered FDM sections), substituted
with full file contents on every render - even though the Phase 3 setup step
already read those exact documents into the orchestrating context. For an inline
render the substitution is pure duplication: the model attends to a second copy of
text it already holds. Anchoring on the pasted copy is also suspected of
suppressing latent-knowledge use (improvement plan item 5's diagnosis).

The same template must still serve cold contexts: the quality gate's `claude -p`
fix rounds today, and item 15's routed part authoring later. A cold context has no
ambient references, so for it the substitution is not duplication but the only
source.

## Goals / Non-Goals

**Goals:**
- Inline part prompts shrink by the reference payload (~10k tokens) per render
  with no information loss (the documents remain in context from Phase 3 setup).
- One template serves both rendering modes; the mode decision is explicit in
  SKILL.md, not inferred.
- Effect measurable through `build/attempts.jsonl` prompt-size telemetry and the
  eval scorecard.

**Non-Goals:**
- No change to which documents are authoritative or how they are tag-filtered for
  cold contexts and planning.
- No condensing of the reference documents themselves (item 14, telemetry-gated).
- No change to `prompts/planning.md` (renders once per build).
- Not building item 15's routing; only keeping its cold path viable.

## Decisions

1. **Citation block, not placeholder deletion.** The placeholders stay in
   `prompts/part.md`; inline rendering substitutes them with a short citation
   section ("Apply `reference/CadQuery Pattern Reference.md` and
   `reference/CadQuery Anti-Patterns.md`, already read in Phase 3 setup; for this
   part the relevant FDM sections are: <list from tag filter>"), while cold
   rendering substitutes full contents as today. Rationale: one template, two
   substitution values - no template fork to drift. Alternative (two templates)
   rejected: every future part.md edit would need mirroring.

2. **The tag filter still runs inline - it just emits section names.** The
   per-part FDM relevance computation (`applies_to` intersection with
   `blocks_needed`) is kept for inline renders, but its output becomes the list of
   section names to apply rather than the section bodies. This preserves the
   filter's targeting value (telling the model which rules matter for this part)
   at ~1% of the token cost.

3. **Phase 3 setup read becomes a hard precondition.** SKILL.md already has the
   setup step read the references; the substitution-table change adds an explicit
   rule: inline citation rendering is valid only after those reads happened in
   this session. If the session cannot confirm it (e.g. resumed context), re-read
   the documents before the first part render. This closes the correctness hole of
   citing documents that are not actually in context.

4. **Text-part gating carries over to citations.** `emboss_text.md` is cited only
   for text/emboss parts, mirroring the existing injection gate, so the citation
   block is computed from the same per-part attributes as today.

5. **Retry prompts inherit the same mode.** A retry within the inline part loop is
   also inline, so it cites; the gate's `claude -p` fix prompt remains cold and
   keeps full substitution. No new mechanism - this falls out of "mode follows the
   rendering context".

## Risks / Trade-offs

- [Model under-attends to cited-but-not-pasted rules] -> The A/B is cheap: run the
  eval corpus (item 8) before and after; first-shot pass rate and attempts-to-pass
  are the guardrail metrics, cost per accepted part the target metric. Revert is a
  one-file change.
- [Resumed or compacted session lost the reference content] -> Decision 3's
  precondition rule: re-read before first render when setup reads are not in the
  visible session.
- [Cold path silently loses substitution if the citation value is used by mistake]
  -> SKILL.md substitution table states the rule as mode-keyed; the gate's
  existing `claude -p` path is untouched code-wise.
- [Spec drift with reference-injection spec] -> Handled as MODIFIED requirements in
  this change's delta spec, keeping one source of truth.

## Migration Plan

One commit: edit `prompts/part.md`, edit the SKILL.md substitution table. No code
or schema changes; rollback is `git revert`. Before/after eval run recorded in the
change's notes (scorecard.json diff).

### Eval comparison (2026-07-20/21, full 10-case corpus, `--generate`)

Full runs at `evals/runs/before-citation/` (pre-change) and
`evals/runs/after-citation/` (post-change), scorecards in each directory.

| Metric | Before | After | Delta |
|---|---|---|---|
| First-shot rate (aggregate) | 0.80 | 0.70 | -0.10 |
| Attempts-to-pass (aggregate) | 1.40 | 1.30 | -0.10 (better) |
| Cost/accepted part (USD, aggregate) | 0.1845 | 0.0722 | -61% |
| Mean `prompt_chars` (telemetry, all attempts) | 33430 | 15513 | -54% |

**Target metric (cost per accepted part) improved by 61%**, and mean rendered
prompt size dropped 54% — both consistent with removing the ~10k-token reference
duplication from inline (progressive-part) renders while autonomous parts'
cold-context builder-agent renders keep full substitution (their `prompt_chars`
stayed near the pre-change max, ~53k, confirming the mode split is working as
designed).

**Guardrail check:** the one first-shot regression (`adapter-ring`, 1.00 -> 0.00)
is fully attributable to a single attempt-1 `occ_exception` (an OpenCASCADE
geometry-kernel error, unrelated to reference-doc comprehension) before passing
on attempt 2 — not a citation-comprehension failure. `attempts-to-pass` improved
in aggregate because `phone-stand` needed fewer retries (4 -> 2) after the
change, outweighing `adapter-ring`'s one extra attempt. With n=1 per case, a
single flaky geometry failure is within ordinary run-to-run noise, not a
signal attributable to this change. No case regressed in a way traceable to a
model failing to apply a cited-but-not-pasted rule.

Two eval-harness runs each independently hit the Claude account's own session
usage limit partway through generation (`You've hit your session limit`) and
had to be resumed per-case after the reset; this is an artifact of running the
harness's nested unattended `claude -p` calls back-to-back in one sitting, not
a defect in either the harness or this change.

## Open Questions

- Whether the citation block should also name the specific anti-pattern entries
  relevant to the part's blocks (finer targeting) or stay at document granularity.
  Default: document granularity; finer targeting is item 14 territory.
