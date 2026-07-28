# Claude 5 Series Conversion Plan

Adapt cq-design's prompts, review loops, and model routing to the Claude 5 family
(Fable 5 / Opus 5 / Sonnet 5). Written 2026-07-28; detailed enough to execute in a
later session with Sonnet 5 or Opus 5.

## Why the 5 series needs different prompting (source: Anthropic migration guide)

The guide sections "Migrating to Claude Opus 5 / Sonnet 5 / Fable 5" (available via
the claude-api skill, `shared/model-migration.md`, or
https://platform.claude.com/docs/en/about-claude/models/migration-guide.md) boil
down to these behavioral shifts, all directly relevant to this repo:

1. **Over-prescriptive prompts reduce output quality.** State goals and
   constraints, not enumerated steps. Prompts tuned for 4.x-era models are often
   too prescriptive for 5-series models.
2. **Literal instruction following.** "CRITICAL / MUST / ALWAYS" language
   over-triggers; severity filters in review prompts depress measured recall
   (the model finds the bugs, then declines to report them).
3. **Self-verification is built in.** Instructions telling the model to verify,
   double-check, or use a verification pass now cause over-verification. The fix
   is a delete, not a rewrite.
4. **Scope expansion.** Add an explicit scope-discipline instruction ("deliver
   what was asked, at the scope intended; finish the whole task").
5. **Opus 5 delegates to subagents readily** (opposite of 4.8). Remove any
   "delegate more" guidance; add explicit caps where subagents exist.
6. **Longer output by default.** Conciseness and deliverable-length instructions
   work; lowering effort does not reliably shorten visible output.
7. **Effort ladder matters.** low/medium on Opus 5 / Sonnet 5 often match prior
   models' high; sweep instead of carrying old defaults.
8. **Grounded progress claims.** Require claims audited against tool results
   (relevant for autonomous part-builder agents and telemetry honesty).

Model IDs for this conversion: `claude-opus-5`, `claude-sonnet-5`,
`claude-fable-5`. Pricing (per MTok in/out): Opus 5 $5/$25, Sonnet 5 $3/$15
(intro $2/$10 through 2026-08-31), Fable 5 $10/$50, Haiku 4.5 $1/$5.

## Relationship to IMPROVEMENT_PLAN.md

Do NOT finish IMPROVEMENT_PLAN.md first. Three of its five open items are the
same work as this conversion and should land inside it:

| IMPROVEMENT_PLAN item | Fold into | Why |
|---|---|---|
| 10 (gate report-only by default) | C4 | Identical to the 5-series "delete verification scaffolding" guidance |
| 14 (condense references) | C5 | Reference dumps suppress latent knowledge; 5-series makes this worse |
| 15 (finish model routing) | C6 | Needs the 5-series model names and prices anyway |
| 5 section 4 (engineering-hooks A/B) | C7 | Run the A/B on the 5-series baseline, not the old one, or the measurement is wasted |
| 9 (typed OCC errors) | independent | Pure Python change, no prompting interaction; do whenever |

After this plan lands, update IMPROVEMENT_PLAN.md statuses for 5, 10, 14, 15.

## Execution model

- **Opus 5** for phases C2-C5 (judgment-heavy prompt rewriting, review-layer
  collapse, reference condensation). This is low-volume, high-leverage editing
  where a wrong cut costs eval regressions.
- **Sonnet 5** is fine for C1 and C6 (mechanical: config plumbing, price tables,
  telemetry field, agent files).
- Every phase's acceptance criterion is the eval harness
  (`evals/run_evals.py`), never inspection alone.

---

## C1. Baseline measurement (do first, mechanical)

Before touching any prompt, capture a before-scorecard so every later change is
measurable.

- Run `evals/run_evals.py --generate` once on the current prompts with the
  session's current model; keep the run dir and `scorecard.json` as
  `evals/runs/baseline-pre-claude5/` (or wherever run dirs live).
- Update `evals/model_prices.json` with the 5-series entries:
  `claude-opus-5: {in: 5, out: 25}`, `claude-sonnet-5: {in: 3, out: 15}`,
  `claude-fable-5: {in: 10, out: 50}` (USD per MTok; note Sonnet 5 intro
  pricing $2/$10 until 2026-08-31 in a comment if the format allows).
- `src/telemetry.py`'s `model` field: make the part loop record the actual
  authoring model per attempt (currently effectively hardcoded per
  ARCHITECTURE.md line ~140). Cheap and required for C6's A/B.

Acceptance: baseline scorecard exists; telemetry rows carry a real model id.

## C2. De-prescribe prompts/part.md (Opus 5)

The part prompt is the highest-volume surface. Changes:

1. **Collapse the 13-point "You should" list.** Keep hard contract rules as
   rules (they are machine-consumed): flat `from blocks import ...`, `result`
   variable / unions dict, no `cq.exporters.export`, PARAMETERS section, no
   OpenSCAD, no changelog comments. Fold the behavioral items (2, 8-12:
   "elegant, maintainable", "clear, commented, parametric", "follow best
   practices", "use selectors", "primary shape first") into one or two
   goal-stating sentences. Enumerated craft advice is exactly the
   prescriptiveness the guide says to remove.
2. **Soften modal language where it is guidance, not contract.** "The computed
   check MUST reference this script's own parameter names" can stay (it is a
   checkable contract). But scan for SHALL/MUST/NEVER used for style guidance
   and rewrite as plain statements. (Grep count today: only ~5 hits across
   prompts/skill, so this is small.)
3. **Comment density.** Replace "Generate clear, commented code" with the
   5-series comment rule: comments only for constraints the code cannot show;
   never narrating what the next line does. This also reduces token cost of
   generated scripts.
4. **Keep the ENGINEERING RATIONALE block and cq_verify guard requirements
   unchanged** - they are elicitation hooks and typed-error contracts, not
   prescriptive scaffolding, and item 5's A/B (C7) will judge them.
5. **Scope discipline for the builder.** Add one instruction (adapted from the
   migration guide): "Build exactly the part specified. Do not add features,
   interfaces, or guards beyond the spec and the required cq_verify points; do
   not refactor or restructure on a retry beyond the reported error."
6. **Retry prompts** (wherever Phase 3 renders correction prompts,
   `skill/phase3_build.md`): drop any "double-check / re-verify your fix"
   phrasing - Opus 5/Sonnet 5 self-verify; such lines now cause
   over-verification and extra tokens.

Acceptance: eval first-shot rate and attempts-to-pass no worse than C1
baseline; generated-script token size expected to drop.

## C3. prompts/planning.md and phase files (Opus 5, light touch)

Planning is contract-heavy (schema, coordinate frame, request_log rules) - keep
it. Targeted edits:

1. The "ask the user" rules (dimension unknowns, load ambiguity, fit type) are
   correct and stay. But add the minor-decision carve-out so 5-series
   deliberateness does not flood the user with questions: "For minor choices
   (a coined part name, a default clearance within the table, plate grouping),
   pick a reasonable option and record it in planning_notes; ask only when
   different answers change the topology, a dimension, or a fit."
2. Scan `skill/phase1_requirements.md` - `phase4_deliver.md` and `SKILL.md` for
   step-by-step scaffolding a 5-series model no longer needs (forced progress
   summaries, "after each step report X", re-check instructions). Delete forced
   narration scaffolding; keep user checkpoints (those are review policy, not
   narration).
3. `review_policy` semantics unchanged - user checkpoints are intent capture,
   not model verification, and are exempt from the "delete verification" rule.

Acceptance: plan-stage eval cases still validate; no increase in clarifying
questions on the eval corpus requests.

## C4. Collapse review layers (= IMPROVEMENT_PLAN item 10) (Opus 5)

The 5-series guidance ("delete verification scaffolding", "report everything,
filter downstream") is the rationale for finishing item 10 now:

1. `src/quality_gate.py`: flip the default to report-only (`allow_fix` off
   unless `--fix` passed; invert the current `--no-fix`). Route gate findings
   back into the inline part-loop fix path in `skill/phase3_build.md` (the
   orchestrating Claude fixes with full context instead of a cold `claude -p`).
   Keep `_call_claude` for explicit `--fix` runs.
2. Visual review checklist (`reference/Visual Review Checklist.md`): rewrite
   filtering instructions to coverage-first: "Report every discrepancy you see
   with a confidence and severity; do not withhold low-confidence findings -
   the fix decision filters, not the review." Severity-filtered review prompts
   depress recall on 5-series models.
3. Remove any explicit "verify your work with a render before finishing" step
   from the part loop's self-review path under `minimal` policy - the model
   does this unprompted; keep the deterministic checks (lint, wrapper,
   feature-presence) which are programs, not prompts.

Acceptance: attempts-to-pass and cost per accepted part improve or hold; no
regression in caught-defect rate on the eval corpus goldens.

## C5. Condense references (= IMPROVEMENT_PLAN item 14) (Opus 5)

Now unblocked by telemetry and reinforced by 5-series behavior (pasted prose
anchors attention and suppresses latent knowledge).

1. Use `build/attempts.jsonl` history across eval runs to find which
   `reference/CadQuery Pattern Reference.md` / `CadQuery Anti-Patterns.md`
   sections correlate with avoided (or unavoided) error types.
2. Cut prose tutorials; keep what the model cannot recall: exact API gotchas,
   OCC failure signatures, numeric tables. Target -40% per the original item.
3. Archetype templates already carry common idioms implicitly - lean on that.
4. Cold-context renders (subagents, `claude -p`) substitute the condensed
   versions, shrinking C6's cost equation.

Acceptance: eval scorecard no worse than post-C4; rendered part-prompt token
count measurably down (telemetry `prompt size` field).

## C6. Model routing with 5-series names (= IMPROVEMENT_PLAN item 15) (Sonnet 5 ok)

1. New `skill_config.json` (seeded like `printer_profile.json`), `models`
   section: `{"planner": "claude-opus-5", "part_author": "claude-sonnet-5",
   "fix_loop": "inline"}`. Planner may be raised to `claude-fable-5` for the
   hardest topology work; note in the config comment that Fable is 2x Opus 5
   price and its extra capability targets long-horizon work, not one-shot
   planning - measure before defaulting to it.
2. Ship `.claude/agents/cq-part-author.md` (and optionally `cq-planner.md`)
   with `model:` frontmatter read from / matching `skill_config.json`. The
   builder prompt is already self-contained for cold context (item 13's
   exception), so this is wiring, not prompt work.
3. `src/quality_gate.py` `_call_claude`: pass `--model` from `skill_config.json`
   when the fix loop is explicitly enabled (post-C4 it is opt-in).
4. **Subagent caution (new, 5-series specific):** if the orchestrating session
   runs on Opus 5, it will delegate more readily than 4.8 did. The Phase 3
   routing gate (`review_policy` first, complexity second) must remain the only
   thing that decides agent dispatch - do not add "prefer subagents" language
   anywhere, and state in `skill/phase3_build.md` that one part = at most one
   builder agent, no verification subagents.
5. A/B on the eval set: Opus-5-inline authoring vs Sonnet-5-subagent authoring,
   scored by cost per accepted part and first-shot rate (telemetry now records
   the model per attempt from C1).

Acceptance: routing configurable without editing skill files; A/B scorecards
archived; pick the cheaper configuration that holds first-shot rate.

## C7. Re-run the engineering-hooks A/B (= IMPROVEMENT_PLAN item 5 section 4)

On the post-C6 configuration, run the eval corpus with the ENGINEERING
RATIONALE hooks on vs off (hooks stripped from the rendered prompt). 5-series
models have stronger latent engineering knowledge, so the hook's value must be
re-established, not assumed. Update IMPROVEMENT_PLAN item 5 to DONE (or revert
the hooks) based on the result.

## C8. Autonomy and honesty instructions for autonomous runs (Opus 5, small)

For `review_policy: minimal` (autonomous) runs, add to the builder/orchestrator
guidance in `skill/phase3_build.md`:

- Grounded progress: "Before recording an attempt outcome or reporting a part
  as passing, point to the wrapper JSON or check output that shows it. Never
  report a state you have not observed in a tool result this session."
- No mid-part permission questions under `minimal`: proceed on reversible
  decisions, record them, surface at the next checkpoint.

These are near-verbatim from the Fable/Opus 5 guidance for long-running agents
and directly protect `build/attempts.jsonl` integrity.

## Suggested order and sizing

| Phase | Model | Size | Depends on |
|---|---|---|---|
| C1 baseline + prices + telemetry | Sonnet 5 | small | - |
| C2 part.md de-prescription | Opus 5 | medium | C1 |
| C3 planning/phase files | Opus 5 | small | C1 |
| C4 review-layer collapse | Opus 5 | medium (code + prompt) | C1 |
| C5 reference condensation | Opus 5 | medium | C1, ideally after C2/C4 telemetry |
| C6 model routing | Sonnet 5 | small-medium | C1; benefits from C5 |
| C7 hooks A/B | either (runs evals) | small | C6 |
| C8 autonomy instructions | Opus 5 | small | C2 |

Each of C2-C6 ends with an eval run compared against the previous scorecard;
revert any change that regresses first-shot rate or cost per accepted part.
