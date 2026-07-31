## Context

`prompts/part.md` is 234 lines and is rendered once per part per attempt, in two modes
(inline citation, or cold-context full substitution for a subagent / `claude -p`). Its
first 37 lines are the authoring instructions: a 13-item "You should" list and a 6-item
"You should NOT" list. Everything after line 38 -- coordinate vocabulary, block specs,
part specification, script structure, engineering rationale, `cq_verify`, construction
plan, reference substitution -- is contract or injected content.

The 13 items are not homogeneous. Six are contracts the pipeline enforces mechanically:

| part.md item | Enforced by |
|---|---|
| 4 (flat block import) | `script_lint.py` `submodule_import` |
| 5 (PARAMETERS, no magic numbers) | `script_lint.py` `magic_number` |
| 7 (`result` binding / unions dict) | `script_lint.py` `missing_result`, `units.resolve_unions` |
| 13 (`cq_verify` guards) | `script_lint.py` `unguarded_boolean`, typed wrapper errors |
| NOT-1 (no `cq.exporters.export`) | `script_lint.py` `direct_export` |
| NOT-6 (no changelog comments) | `request-log` capability, read on review |

The other seven (1, 2, 3, 6, 8, 9, 10, 11, 12) are craft advice with no detector. That
split is the whole basis for this change: the first group stays enumerated because a
downstream program reads it; the second collapses because the 5-series migration guidance
says enumerated craft advice measurably lowers output quality.

C1 established the baseline this change is measured against:
`evals/runs/baseline-pre-claude5/scorecard.md` -- first-shot 0.70, attempts-to-pass 1.30,
chamfer 3.118 mm, cost/part $0.0078 over 10 cases.

## Goals / Non-Goals

**Goals:**

- Remove enumerated craft advice from `prompts/part.md` without weakening any rule the
  pipeline mechanically enforces.
- Cut generated-script comment volume by replacing the generic "commented code" directive
  with a constraint-only comment rule.
- Give the builder an explicit scope boundary, on the first attempt and on retries.
- Hold the C1 eval baseline; measure rather than assume.

**Non-Goals:**

- The ENGINEERING RATIONALE block, the `cq_verify` guard rules, and the `verify_stage`
  construction plan. C7 runs the hooks A/B; touching them here would confound it.
- `prompts/planning.md` and the phase files' step scaffolding -- that is C3.
- Review-layer collapse and the visual-review checklist -- that is C4.
- Reference condensation (`{{CQ_REFERENCE}}`, `{{FDM_GUIDELINES}}`) -- that is C5, and it
  is what makes the cold-context render expensive, not this section.
- Fixing `planning-phase`'s stale block-import requirement (noted in the proposal).

## Decisions

**D1. Split by detectability, not by topic.** A rule stays an enumerated directive iff a
program or a mechanical read can catch its violation. This gives an objective test for
every line rather than a judgment call about what "feels prescriptive", and it means the
lint suite is the floor: prose can loosen, enforcement cannot.

*Alternative considered:* keep the numbered list and only soften its wording. Rejected --
the migration guidance names the enumerated form itself, not the wording, as the problem.

**D2. Two paragraphs, not one.** The collapsed guidance becomes a short "what good output
looks like" paragraph plus a separate scope-discipline sentence, rather than a single
dense paragraph. Scope discipline reads as a boundary, not as a quality aspiration, and
burying it inside craft prose would blunt it.

**D3. Keep the "You should NOT" list.** Five of its six items are contracts (no export
call, no OpenSCAD, no changelog narrative) or role boundaries (no FEA, no aesthetic
judgment, no GUI assumptions). Negative contracts are the case where enumeration is
clearest, and the migration guidance's objection is to prescribed *procedure*, not to
stated prohibitions.

**D4. Comment rule is stated once, with its exemptions named inline.** Without naming the
ENGINEERING RATIONALE block and `verify_stage` labels as exempt, a literal reading of
"comments carry constraints, not narration" could suppress required content -- the
5-series literal-instruction-following failure mode. The exemption sentence costs one line
and removes the ambiguity.

**D5. Retry scope lands in both surfaces.** `prompts/part.md` is what a cold builder agent
sees; `skill/phase3_build.md` Step 2 is what the inline orchestrator follows. Its existing
line ("Do not start over blindly -- you have full planning context") already carries the
spirit; this change makes the boundary explicit in the same paragraph rather than adding a
second one.

**D6. No deletion for "double-check / re-verify" phrasing.** The plan anticipated stripping
it. A grep of `prompts/**/*.md` and `skill/**/*.md` for `double-check|re-verify|verify
your|make sure|be sure to|check again|carefully` returned two hits, both unrelated
(`phase2_planning.md:65` describes a plan property; `phase3_build.md:212` describes
rationale evaluation). Recording this so a later reader does not re-search for a deletion
that was never available.

**D7. Measure token size by instrumenting the render, not by self-report.** The change
predicts smaller rendered prompts and smaller generated scripts. The original plan assumed
`build/attempts.jsonl` already records a usable per-attempt prompt size for free. It
doesn't: the field is `prompt_chars`, not `prompt_size`, and `skill/phase3_build.md` Step
5 populates it by asking the executing model to type `<len of the rendered step-1
prompt>` -- a guess, not a measurement. Across the baseline and c2-subset runs it was `0`
in 2 of 6 and 1 of 3 attempts respectively, and every nonzero value is a round number a
model typed (13200, 13500, 9000, 14000), not a computed length. The one case with data in
both runs (`sliding-lid`) went up, not down (13200 -> 14000). None of this supports a
token-size claim in either direction.

Fix: Step 1's prompt rendering (placeholder substitution against `prompts/part.md`, in
either render mode) must write the rendered prompt to a file before the attempt runs, so
`prompt_chars` is computed from that file's actual character count -- e.g. `python -c
"import sys,pathlib;print(len(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')))"
<rendered_prompt_file>` -- rather than typed by the executor. `skill/phase3_build.md` Step
5's telemetry call is updated to use that measured value. It remains reported, not gated --
a size increase with a quality hold is acceptable; a quality regression is not. Existing
baseline and c2-subset `prompt_chars` values are self-reported and must not be used for a
before/after comparison; only runs recorded after this fix land are comparable.

*Alternative considered:* drop the token-size claim entirely and report only quality
metrics. Rejected -- prompt size is the change's stated mechanism (a shorter rendered
prompt), not an incidental side effect, and the fix is one measured file length per
attempt with no new dependency.

## Risks / Trade-offs

**Collapsed guidance loses a rule that had no detector but was load-bearing** (e.g.
"selectors and relative positioning for more robust models" may be why parts survive
parameter changes) -> The eval corpus is the detector: 10 cases with golden meshes and
Chamfer distance. A quality drop shows up as first-shot rate or Chamfer, and D1's split is
documented per item so a revert can restore one line rather than the whole section.

**Scope-discipline instruction over-constrains and suppresses a needed guard** -> The
instruction scopes to "beyond the spec and the required `cq_verify` points", which names
the guards as in-scope rather than as an addition. `unguarded_boolean` in `script_lint.py`
still fails a script that drops a required guard, so the failure is caught at Step 2.5,
before a run.

**Comment rule strips the ENGINEERING RATIONALE block on a literal reading** -> D4's
inline exemption, plus `engineering-rationale`'s own scenarios remain the contract. The
eval corpus includes load-bearing cases (`u-clip`, `snap-lid`, `l-bracket`, `wall-hook`)
whose scripts can be read for the block after the run.

**Both render modes change at once, so a regression cannot be attributed to one** -> The
substitution table is untouched, so the delta is identical in both modes; there is no
mode-specific hypothesis to isolate. If a regression appears, the revert is the whole
section, not one mode.

**Baseline is 10 cases with 3 already at first-shot 0.00** -> Small-n noise can mask or
manufacture a regression. Treat a single-case flip as noise; require the aggregate
first-shot >= 0.70 and attempts-to-pass <= 1.30 to accept, and re-run before reverting on
a marginal miss.

## Migration Plan

1. Edit `prompts/part.md` and `skill/phase3_build.md` (no code, no schema).
2. Run the eval harness with `--generate` into a new run dir
   (`evals/runs/c2-de-prescribed/`).
3. Compare `scorecard.md` against `evals/runs/baseline-pre-claude5/scorecard.md`.
4. Accept on hold-or-better; otherwise revert the two files in one commit.

Rollback is `git revert` of a single documentation commit. No state, no artifacts, no
data migration -- a rendered prompt is built fresh each attempt, so the previous prompt is
in effect on the next run with no cleanup.

## Open Questions

- Whether the collapsed guidance should name CadQuery selectors at all. Item 11 is the one
  piece of craft advice that is CadQuery-specific rather than general good practice, so it
  is the most plausible candidate for latent knowledge the model does *not* have. Current
  decision: collapse it with the rest and let the eval say; if first-shot drops, restore
  that one clause before reverting the whole section.
