## Why

`prompts/part.md` was tuned for 4.x-era models: a 13-item enumerated "You should" list
that mixes machine-checkable contract rules with craft advice ("elegant, maintainable",
"follow CadQuery best practices", "use selectors", "build the primary shape first").
The Claude 5 migration guidance is explicit that over-prescriptive step enumeration
lowers output quality on 5-series models, and that pasted craft advice suppresses latent
knowledge the model already has. The part prompt is the highest-volume surface in the
skill -- it is rendered once per part, per attempt, in both inline and cold-context modes
-- so it is where de-prescription pays the most.

This is phase C2 of `CLAUDE5_CONVERSION_PLAN.md`. C1 is done: `evals/runs/baseline-pre-claude5/`
records first-shot 0.70, attempts-to-pass 1.30, cost/part $0.0078 across 10 cases, which
is the number this change must hold.

## What Changes

- **Collapse the enumerated "You should" list in `prompts/part.md`.** The behavioral items
  (1, 2, 8-12: elegant/maintainable, "Design as Code" philosophy, core API, commented code,
  best practices, selectors, primary-shape-first) become one or two goal-stating sentences.
  The machine-consumed contract rules stay enumerated and unambiguous: flat
  `from blocks import ...`, `result` variable / unions dict, no `cq.exporters.export`,
  PARAMETERS section with no magic numbers, no OpenSCAD, no round-by-round changelog
  comments, `cq_verify` guards at the documented risk points.
- **Add a comment-density rule.** Replace "Generate clear, commented, parametric code" with
  the 5-series rule: a comment carries a constraint the code cannot show; it never narrates
  what the next line does. Secondary effect: smaller generated scripts, less token cost per
  attempt and per re-read.
- **Add a scope-discipline instruction** for the builder: build the specified part at the
  specified scope; do not add features, interfaces, or guards beyond the spec and the
  required `cq_verify` points; on a retry, edit what the reported error names rather than
  restructuring the script.
- **Reserve modal language (MUST/SHALL/NEVER) for checkable contracts.** Audited surface is
  small: 2 hits in `prompts/part.md` (both contract, both stay), 2 in `prompts/planning.md`
  (out of C2's scope), 0 in `skill/`.
- **Retry prompts (`skill/phase3_build.md`):** carry the same scope-discipline framing.
  The plan anticipated stripping "double-check / re-verify your fix" phrasing; an audit of
  `prompts/` and `skill/` found no such phrasing, so no deletion is needed there.
- **Unchanged on purpose:** the ENGINEERING RATIONALE block, the `cq_verify` guard
  requirements, and the `verify_stage` construction plan. These are elicitation hooks and
  typed-error contracts, not prescriptive scaffolding; C7's A/B is what judges the hooks.

## Capabilities

### New Capabilities
- `part-authoring-guidance`: How `prompts/part.md` frames the authoring task -- goals and
  constraints stated rather than craft steps enumerated, the comment-density rule, the
  builder's scope discipline (including on retries), and the rule that modal language is
  reserved for checkable contracts. Covers the boundary between contract rules (which stay
  enumerated) and behavioral guidance (which does not).

### Modified Capabilities

None. The requirements that touch `prompts/part.md` today -- `engineering-rationale`,
`runtime-boolean-verification`, `block-import-injection`, `request-log`, `reference-injection`,
`subagent-orchestration` -- each own a contract rule that this change preserves verbatim in
meaning. Restructuring the prose around them does not change what they require.

## Impact

- `prompts/part.md`: the "Your task" / "You should" / "You should NOT" sections rewritten;
  everything from "Coordinate vocabulary" onward structurally unchanged.
- `skill/phase3_build.md`: Step 2's "On retry attempts" paragraph gains the scope-discipline
  framing.
- Both render modes are affected (inline and cold-context subagent / `claude -p`), since both
  render the same template. No substitution placeholders change, so `reference-injection`'s
  mode table stays valid.
- No Python changes. No schema changes. `src/script_lint.py` already enforces the contract
  rules that stay (magic numbers, missing `result`, submodule imports, direct export), so
  loosening prose does not loosen enforcement.
- Acceptance is the eval harness against `evals/runs/baseline-pre-claude5/`, not inspection:
  first-shot >= 0.70 and attempts-to-pass <= 1.30 aggregate. Revert if either regresses.

### Observed out of scope

`openspec/specs/planning-phase/spec.md:171` ("Part prompt instructs LLM not to write block
imports") contradicts `block-import-injection` and the current `prompts/part.md`, both of
which require the script to self-declare flat imports. Pre-existing staleness, unrelated to
de-prescription; left for a separate change so this one stays revertible as a single unit.
