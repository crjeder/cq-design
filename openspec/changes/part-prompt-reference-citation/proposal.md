## Why

Phase 3 setup already reads the CadQuery pattern reference, anti-patterns, and
tag-filtered FDM guide into the orchestrating context once - then the
`{{CQ_REFERENCE}}`/`{{FDM_GUIDELINES}}` placeholders re-substitute ~10k tokens of
the same documents into every rendered part prompt, multiplied by part count and by
the prompt's presence across retry attempts. Improvement plan item 13: cite the
already-loaded documents by name in inline part prompts and substitute only what is
per-part. Largest single token saving after the SKILL.md split, with zero
information loss inline.

## What Changes

- `prompts/part.md`: replace the `{{CQ_REFERENCE}}` and `{{FDM_GUIDELINES}}`
  placeholder blocks with a short citation section naming the documents already in
  context (pattern reference, anti-patterns, `emboss_text.md` when the part
  involves text, the FDM sections relevant to the part's blocks) and instructing
  their application. Only the part spec, block specs, and constraints remain
  substituted per part.
- SKILL.md Step 1 substitution table: drop the two reference placeholders from the
  inline rendering path; require the Phase 3 setup reads (already specified) as the
  precondition that makes citation valid.
- **Cold-context exception preserved**: any part prompt sent to a fresh context - a
  `claude -p` subprocess or a subagent - still gets full placeholder substitution,
  because a cold context has no ambient references. The template keeps working for
  both modes: placeholders remain defined for cold rendering; inline rendering
  substitutes them with the citation block instead of file contents.
- Planning prompt (`prompts/planning.md`) is untouched: planning renders once per
  build, so its `{{FDM_GUIDELINES}}` substitution is not a multiplier.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities
- `reference-injection`: the part-prompt injection requirements change from
  "substitute full contents into every rendered part prompt" to "cite in-context
  documents for inline rendering; substitute full contents only for cold-context
  invocations". Tag-filtering and once-per-build loading requirements are rescoped
  accordingly.

## Impact

- `prompts/part.md`, SKILL.md Phase 3 Step 1 substitution table.
- No src/ code changes (rendering is performed inline by the orchestrating Claude).
- Interacts with improvement plan item 15 (model routing): routed part authoring is
  a cold context and pays full substitution - that cost equation belongs to item 15
  and is unaffected by this change.
- Measurable via the eval harness (item 8): prompt-size fields in
  `build/attempts.jsonl` should drop by roughly the reference payload per attempt
  with no regression in first-shot pass rate.
