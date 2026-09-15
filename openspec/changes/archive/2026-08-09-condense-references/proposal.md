## Why

The two largest injected documents (`reference/CadQuery Pattern Reference.md`, 23.7 KB;
`reference/CadQuery Anti-Patterns.md`, 13.1 KB) are pasted in full into every
cold-context part render, and cold renders dominate prompt size: measured
`prompt_chars` in `evals/runs/c2-prompt-chars` ranges from 1,018 (inline) to 173,166
(cold). Beyond cost, 5-series models treat pasted prose as an attention anchor that
suppresses latent knowledge they already have -- so tutorial content that restates what
the model knows is not neutral filler, it actively degrades output. This is
CLAUDE5_CONVERSION_PLAN C5 (= IMPROVEMENT_PLAN item 14), unblocked now that telemetry
records a real prompt size.

## What Changes

- Establish a content rule for injected reference documents: keep only what the model
  cannot reliably recall (exact API signatures and gotchas, OCC failure signatures,
  numeric tables, project-specific contracts); cut prose tutorials, restated
  fundamentals, and idioms the archetype templates already demonstrate.
- Condense `reference/CadQuery Pattern Reference.md` and
  `reference/CadQuery Anti-Patterns.md` to ~60% of current size against that rule,
  using `build/attempts.jsonl` across the archived eval runs as the evidence for which
  sections earn their place.
- Ground each cut in evidence rather than taste: an error type that appears in attempt
  history keeps its section; a section with no corresponding error class and no
  non-recallable content is a cut candidate.
- Measure before/after with an eval sweep, comparing scorecard metrics against the
  post-C4 run and mean cold-render `prompt_chars` against `c2-prompt-chars`.
- Record the outcome in `CLAUDE5_CONVERSION_PLAN.md` (C5 result block, matching the
  C2/C3/C4 format) and update `IMPROVEMENT_PLAN.md` item 14.

No change to injection mechanics: mode split, tag filtering, and citation rules stay
exactly as specified today. Only the documents' contents shrink.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reference-injection`: adds a requirement constraining the *content* of the injected
  reference documents (non-recallable material only, evidence-backed cuts), alongside
  the existing requirements that govern how they are selected and rendered.

## Impact

- `reference/CadQuery Pattern Reference.md`, `reference/CadQuery Anti-Patterns.md` --
  rewritten (condensed).
- `evals/runs/` -- one new archived run dir + scorecard.
- `CLAUDE5_CONVERSION_PLAN.md`, `IMPROVEMENT_PLAN.md` -- status updates.
- No source code changes. Injection points (`skill/phase3_build.md` setup reads,
  `prompts/part.md` placeholders, `SKILL.md` reference table) keep working unmodified;
  section-name citations remain valid only for sections that survive, so any phase file
  naming a removed section by name must be checked.
