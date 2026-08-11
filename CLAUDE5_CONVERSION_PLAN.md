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

**Result (change `de-prescribe-part-prompt`):** accepted, but on a noisier
basis than the first run suggested — two full 10-case sweeps exist, not one,
and they disagree.

- `evals/runs/c2-de-prescribed/` (before the D7 render-measurement instrumentation
  landed): first-shot 0.85, attempts-to-pass 1.15, Chamfer 3.751mm. Three cases
  (`two-part-box`, `u-clip`, `wall-hook`) hit transient Anthropic API errors
  (500/529) on the first pass and were regenerated before scoring — infra, not
  a quality effect.
- `evals/runs/c2-prompt-chars/` (after the instrumentation landed; same
  `prompts/part.md`, re-run to get a real `prompt_chars`): first-shot 0.75,
  attempts-to-pass **1.35** — passes the first acceptance gate (>= 0.70) but
  misses the second (<= 1.30) by 0.05. Chamfer 3.449mm. Disagrees with the
  first run per-case on `snap-lid` (1.00 vs 0.00) and `l-bracket` (2 vs 3
  attempts).

Mean across both: first-shot 0.80, attempts-to-pass 1.25 — both better than
the C1 baseline (0.70 / 1.30), which is the basis for calling this accepted.
But the run-to-run spread (0.85/1.15 vs 0.75/1.35) is as large as the entire
measured effect, so a single sweep against the hard threshold cannot separate
C2's effect from noise; don't cite "first-shot 0.85 vs 0.70" without the
second run beside it. Fidelity is flat, not improved: `within_tolerance` is
5/10 at baseline, 3/10 and 5/10 in the two C2 runs; mean Chamfer 3.118mm ->
3.751mm / 3.449mm — neither gated, neither supports a quality-gain claim.

**Token size (design D7):** now measured for real. `c2-prompt-chars` is the
first run with file-measured `prompt_chars` instead of a self-reported guess
— e.g. `adapter-ring` attempt 1: **162952** characters (vs. the old
self-reported guesses of ~8500-14000, which undercounted by an order of
magnitude — they evidently reflected only the visible/typed portion, not the
full cold-mode reference-doc injection). There is no comparable *before*
number: the baseline and `c2-de-prescribed` runs never measured the real
render, only guessed, so no before/after token-size reduction claim can be
made yet — only that a trustworthy number now exists going forward.

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

**Result (change `collapse-review-layers`):** accepted, hold-or-improve on every
gated metric.

- `evals/runs/c4-review-collapse/` (10/10 cases scored): first-shot **0.70**,
  attempts-to-pass **1.30**, mean Chamfer 2.955mm, cost/part $0.0296 (see caveat
  below on cost). Compare `evals/runs/c2-prompt-chars/`: first-shot 0.75,
  attempts-to-pass 1.35, Chamfer 3.449mm, cost/part $0.0512 (10/10 cases); and
  `evals/runs/c3-planning/`: first-shot 0.71, attempts-to-pass 1.29, Chamfer
  2.646mm (only 7/10 cases scored, see below).
- First-shot rate (0.70) and attempts-to-pass (1.30) sit inside the run-to-run
  spread C2's own result section already documents (0.75/1.15 vs 0.75/1.35
  across C2's two runs) - flat, not a regression. Per-case: `boss-plate` and
  `wall-hook` each dropped from a first-shot pass to a 2-attempt pass (both an
  `occ_exception` on attempt 1, fixed on attempt 2); `snap-lid` and
  `two-part-box` each moved the other way, from a C2 retry to a C4 first-shot
  pass. No case needed the gate-driven fix-round path or a failed Implementation
  audit retry that C2/C3 didn't also need at comparable rates.
- Mean Chamfer improved (2.955mm vs C2's 3.449mm, both 10/10 cases) - not a
  gated metric, but no defect-rate regression either.
- Cost per accepted part **caveat:** `adapter-ring` and `boss-plate` were
  generated in an earlier pass of this same sweep (2026-08-07, before the
  Claude account's session usage limit interrupted the run) and carry
  `prompt_chars: 0` in their telemetry - a pre-existing measurement gap in that
  invocation, not something this change touches. Their `cost_per_accepted_part_usd`
  reads $0.0000 and drags the 10-case aggregate down; the other 8 cases (real
  `prompt_chars`) average **$0.0370/part**, still below C2's $0.0512. C3's
  $0.0071 is not a usable cost baseline - it excludes `two-part-box`, `u-clip`,
  and `wall-hook` (its highest-cost cases in C2), whose "no artifacts" rows mean
  C3's own sweep hit the same kind of transient infra failure this run did.
- **Sweep required three passes**, not one: the first (2026-08-07) completed only
  2/10 cases before the account's Claude session usage limit interrupted it
  mid-sweep (`You've hit your session limit`), and a same-day retry of the
  remaining 8 completed 6 before hitting the limit again; the last 2
  (`u-clip`, `wall-hook`) completed the next day after the limit reset. This is
  infra, not a quality effect - consistent with C2's own documented precedent of
  transient API errors requiring case regeneration.

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

**Result (change `condense-references`):** accepted, no regression, prompt size
measurably down; sweep completeness is the caveat.

- `reference/CadQuery Anti-Patterns.md`: 13,118 -> 8,488 bytes (64.7%).
  `reference/CadQuery Pattern Reference.md`: 23,704 -> 15,396 bytes (64.9%).
  Every Tier 1/Tier 2 anti-pattern entry and every Common Gotcha (including the
  numbered #12 cited by `skill/phase3_build.md`) survived condensation; cuts
  concentrated on the pattern reference's recallable/tutorial half (Basic
  Shapes, BRep Vocabulary, Table of Contents, Accessing Objects & Debugging,
  meta-documentation pointer paragraphs) per the evidence-backed retain/cut
  table in `openspec/changes/condense-references/design.md`.
- `evals/runs/c5-condensed/`: two sweep attempts, both interrupted by the
  account's Claude session usage limit before completing all 10 cases (first
  attempt: 2/10; after the reset, second attempt: 9/10 — `wall-hook` hit the
  limit again right at the end). This is the same infra pattern C4's result
  section already documents, not a quality effect. 9/10 was treated as
  sufficient rather than attempting a third sweep.
- Comparing the same 9 cases (excluding `wall-hook` from both sides):
  first-shot rate 7/9 = 0.778 on both C4 and C5-condensed; mean
  attempts-to-pass 11/9 = 1.222 on both. Identical aggregate, but the failing
  cases swapped — C4 failed `boss-plate`/`l-bracket` first-shot, C5-condensed
  failed `l-bracket`/`snap-lid` (`boss-plate` passed first-shot this time).
  This is the same run-to-run spread C2's result section already documents
  (0.85/1.15 vs 0.75/1.35 across two identical-prompt runs) — the aggregate
  holding while individual cases swap is exactly what that spread predicts, not
  evidence of a per-case regression. No case needed the cuts narrowed.
- Cold-render `prompt_chars`: thin sample (n=2 of 11 telemetry records exceed
  the 15,000-char cold/inline split), both from `two-part-box`'s two parts
  (46,885 and 25,452) — mean **36,168.5**, well below the `c2-prompt-chars`
  cold-cluster mean of **90,098.9** (n=7, computed fresh from that run's
  `attempts.jsonl` since C2's own result section never isolated the cold
  subset). Directionally consistent with the ~35% document-size cut but not a
  controlled re-run of the same cold-triggering conditions as C2, so treat as
  supporting evidence, not a matched before/after pair.

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

### C6 result

Config plumbing (skill_config.json, quality_gate.py wiring, subagent cap) landed
as designed in `openspec/changes/model-routing-config`. The `.claude/agents/*.md`
step above was dropped from scope during design review (`design.md`'s
Non-Goals) — the part prompt is already a fully rendered, self-contained
Agent-tool prompt with a per-call model override, so a second file naming the
same model would drift from the config.

**A/B run:** budget constraints reduced the sweep from the full 10-case corpus
to the single case expected to show the largest cost delta —
`two-part-box` (2 parts, so 2x the authoring calls of every other case),
run once per arm rather than the originally planned full-corpus sweep. This is
explicitly a smaller sample than C2's documented run-to-run spread (0.85/1.15
vs 0.75/1.35) was measured over, so treat the numbers below as directional,
not a statistically separated result:

| arm | first-shot | attempts-to-pass | chamfer (mm) | cost/part (USD) |
|---|---|---|---|---|
| opus-inline (`part_author: inline`, orchestrator on `claude-opus-5`) | 1.00 | 1.00 | 0.436 | 0.0184 |
| sonnet-agent (`part_author: claude-sonnet-5`, subagent) | 1.00 | 1.00 | 0.535 | 0.0103 |

Both arms passed first-shot on both parts with no retries and both meshes are
well inside the case's 1.0 mm tolerance. First-shot rate is tied, so it does
not decide between the arms; sonnet-agent is ~44% cheaper per part. That cost
gap is directionally consistent with C6's own hypothesis (Opus 5 pays its
per-token price on every part when run inline; a Sonnet-5 subagent doesn't),
but n=1 case is not enough to rule out run-to-run noise of that size.

**Decision:** sonnet-agent was already the shipped default before this A/B
(`src/skill_config.default.json`'s `part_author: claude-sonnet-5`), and it is
also the arm that came out ahead on this run — no default flip needed. The
full 10-case sweep from tasks 6.1/6.2 was not run; if a future session wants a
statistically separated result, re-run both arms across the whole corpus.

## C7. Re-run the engineering-hooks A/B (= IMPROVEMENT_PLAN item 5 section 4)

On the post-C6 configuration, run the eval corpus with the ENGINEERING
RATIONALE hooks on vs off (hooks stripped from the rendered prompt). 5-series
models have stronger latent engineering knowledge, so the hook's value must be
re-established, not assumed. Update IMPROVEMENT_PLAN item 5 to DONE (or revert
the hooks) based on the result.

### C7 result

Full 10-case corpus, both arms, generated via `evals/run_evals.py --generate`.
The hooks-off arm temporarily stripped the ENGINEERING RATIONALE requirement
from three places -- `prompts/part.md`'s Script structure template (the
commented block between PARAMETERS and MODEL) and its "## Engineering
rationale" prose section, plus `skill/phase3_build.md`'s archetype-path
insertion step and retry-preservation note -- so the archetype-template path
(Step 1.5) couldn't backfill a hook that the stripped `prompts/part.md` no
longer required. Both files were restored via `git checkout` immediately after
the hooks-off sweep finished; the hooks are back in the shipped prompt
regardless of the finding below.

Both sweeps hit the account's session usage limit repeatedly mid-run (same
infra pattern C4/C5/C6 already document) and were resumed case-by-case after
each reported reset; this stretched the two 10-case sweeps across roughly a
day of wall-clock time, not compute time.

- `evals/runs/c7-hooks-on/`: first-shot 0.80, attempts-to-pass 1.20, mean
  Chamfer 3.082mm (10/10 cases scored).
- `evals/runs/c7-hooks-off/`: first-shot 0.80, attempts-to-pass 1.20, mean
  Chamfer 3.278mm (9/10 cases -- `enclosure-body` scored "no artifacts" for
  Chamfer despite a successful first-shot pass and real cost data, a scoring
  gap in that run, not a build failure).
- Aggregate first-shot and attempts-to-pass are **identical** between arms.
  Per-case: `adapter-ring` flipped from a hooks-on first-shot pass to a
  hooks-off 2-attempt pass, and `boss-plate` flipped the opposite direction
  (hooks-on 2 attempts -> hooks-off first-shot) -- the same swap-while-aggregate-holds
  pattern C5's result section already documents, not a hook-driven effect.
  Chamfer delta (3.082mm -> 3.278mm) is within the run-to-run spread C2's
  result section measured (Chamfer swung from 3.118mm to 3.751mm/3.449mm
  across identical-prompt runs) -- not a defect-rate signal either way.
- `two-part-box`'s `cost_per_accepted_part_usd: 0.0000` in the hooks-on
  scorecard is the same pre-existing `prompt_chars: 0` telemetry gap C4's
  result section documents, not a quality effect.

**Qualitative check (the geometric metric can't see this):** spot-checked the
three load-bearing hooks-off scripts most likely to need the hook --
`u-clip`, `l-bracket`, `boss-plate` (clip/bracket/boss, all in the load-bearing
archetype set) -- plus `wall-hook`. All four still opened with a full,
correctly-derived `# ENGINEERING RATIONALE` comment block (load path,
worst-case stress location, a numeric strain/stress check against the
script's own parameter names) **with no prompt requiring it** -- e.g.
`evals/runs/c7-hooks-off/wall-hook/build/wall_hook.py`: `stress =
6*load_F*arm_reach/(width*arm_thickness**2) = 6*20*30/(20*8**2) = 2.81 MPa <=
50 MPa assumed PLA flexural/tensile allowable`. This confirms IMPROVEMENT_PLAN
item 5's premise: on the 5-series, the model volunteers the derivation
unprompted (from the "senior mechanical design engineer" framing and the
still-cited `reference/Engineering Design Rules.md`), not just when the prompt
explicitly demands a comment section in a specific format.

**Decision:** the hook is empirically redundant on Sonnet 5 -- self-elicited
in every load-bearing case checked, with no measured cost to first-shot rate,
attempts-to-pass, or fidelity either way. Keeping it anyway: it's a
zero-marginal-cost deterministic backstop (a few lines added to an
already-large rendered prompt) against the one case this sweep didn't
exercise -- a load-bearing part the model doesn't recognize as load-bearing
without being told to check. No prompt change made; IMPROVEMENT_PLAN item 5
updated to DONE below since the measurement it was blocked on has now landed.

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
