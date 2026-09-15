# Intent recognition

Survey of "intent recognition" as a capability for cq-design: what the skill already
does, where it demonstrably fails, and what outside work is worth adapting. Status /
adoption tracking lives in `TODO.md` (section "From intent-recognition research"), not
here -- this is the survey and the reasoning behind each proposed item.

Surveyed 2026-08. Related surveys: `market_research.md` (LLM-CAD / printability),
`related_projects.md` (per-project adoptable ideas), `Knowledge Domains.md` (which
already names "Geometric Intent Disambiguation" as a required domain without saying
how to implement it).

## TL;DR

- "Intent recognition" is not one capability. It is three: **elicitation** (detect that
  a request is under-specified and ask), **scope classification** (decide what kind of
  change a user utterance asks for, and what it may touch), and **preservation**
  (recheck the finished geometry against the user's own words, not against the plan
  that was derived from them).
- cq-design already does elicitation narrowly (topology + dimensions, Phase 1 only) and
  records intent well (`request_log`). It does **no** scope classification, and its
  acceptance bar is plan-relative, so a plan that misread the request passes every gate
  in the pipeline.
- The highest-value item is the cheapest: **type each `request_log` entry with an
  abstraction level and a target scope at append time.** It reuses machinery that
  already exists and makes the C5 cradle failure class (`TODO.md`) expressible as a
  rule instead of a hope.
- The strongest outside work is ProCAD ("Clarify Before You Draw", arXiv 2602.03045) --
  a clarify-then-generate agent pair for text-to-CadQuery specifically -- and
  LLM4CAD-Editor's functional / operation / parameter intent taxonomy (arXiv
  2606.20607), which is a ready-made vocabulary for scope classification.
- Nothing here ships on vibes: the eval corpus contains no under-specified requests, so
  an intent-recognition change currently has no way to regress. New eval cases are the
  gating cost of the whole idea, not an afterthought.

## The three problems, kept separate

| Problem | Question it answers | Failure when absent |
|---------|--------------------|---------------------|
| **Elicitation** | "Is this request answerable as written, and if not, what one question closes the gap?" | The pipeline guesses, builds, and the user discovers the guess at the design-approval checkpoint (or after printing) |
| **Scope classification** | "What kind of change is the user asking for, and what is it allowed to touch?" | A parameter tweak to one part propagates into a sibling part's independent literal; rounds ping-pong |
| **Preservation** | "Does the delivered model still satisfy what the user actually asked for?" | Intent drifts across generation loops with nothing to detect the drift |

Conflating them produces the usual bad answer ("add an LLM intent classifier"). Kept
separate, each maps to a different existing mechanism in this repo.

## Current state in cq-design

| Surface | What it captures | Where |
|---------|-----------------|-------|
| Topology clarification | Shape ambiguity only, Phase 1 only. Labeled cross-section + a named either/or question; confirmation journaled as `phase1/topology_confirmed` | `skill/phase1_requirements.md` |
| Dimension validation checkpoint | Numeric intent: every looked-up value, its source, and a `confirmed`/`single-source`/`conflict`/`missing` status, user-approved before any plan exists | `skill/phase1_requirements.md` |
| `parameters.py` | Durable provenance of the real-world measurements the design rests on | written at checkpoint approval |
| `request_log` | Verbatim user wording, append-only, never rewritten; typed `initial` / `clarification` / `correction`; optional `images` for sketches | `src/build_plan_schema.json`, `src/request_log_search.py`, `openspec/specs/request-log/` |
| `intent`, `pose_intent`, `optimize_for`, `review_policy` | Intent mapped *into* structured plan fields. `prompts/planning.md` rules 10-11a are literally intent-mapping rules ("Map intent: load-bearing/structural -> `strength`") | `prompts/planning.md`, `src/build_plan_schema.json` |
| Section-selection tiers | The one place a `request_log` `kind` already drives behaviour: interfaces matching a `clarification` entry outrank `correction`, which outranks the rest, when choosing `--extra-section` cuts | `skill/phase3_build.md` Step 3 |
| Implementation audit | Fresh-context render-vs-plan review, question-driven, one question per interface / block / union | `skill/phase3_build.md`, `reference/Visual Review Checklist.md` |

Read together: recording is solid, elicitation is narrow, classification is absent,
verification points at the plan rather than the request.

## Gap 1 -- elicitation is topology-only and Phase-1-only

The clarification rule fires on shape ambiguity ("a recessed pit vs. a raised rim"). It
does not fire on:

- a missing dimension that no lookup can supply (distinct from the `-1` placeholder
  path, which handles a dimension that *should* exist in a source and does not);
- two stated constraints that cannot both hold;
- an **unstated reference frame** -- the C5 compass-language defect in `TODO.md`
  ("east should be right", from mixing "viewed from South" with "south facing") is
  exactly this, and no current gate is capable of asking about it;
- an unstated fit type or load path (the planning prompt tells the planner to ask about
  `load`, but there is no audit that notices it should have);
- part-vs-assembly scope ("make the bracket 5mm taller" -- the bracket, or the stack it
  sits in?).

It also never fires again. After Phase 1, every later utterance is recorded verbatim
and acted on directly; nothing re-audits a mid-build correction for ambiguity, which is
where the ambiguity is most expensive because parts already exist.

## Gap 2 -- corrections are untyped (the expensive one)

`request_log` records *that* the user said something and *whether* it was a
clarification or a correction. It records nothing about **scope**: which part, which
feature, which parameter, at what level of abstraction.

The C5 cradle case (`TODO.md`, session `session-export-1786538430013.zip`) is a
scope-misclassification, not a geometry bug: "align the hole with the bore hole on the
front plate when the leg lies flat on the front plate" was a parameter-level intent
about **one part's own authoring pose**, and raising the cradle's `EAR_STANDOFF` got
mirrored into the stationary plate's independent `PIVOT_Z` literal -- ping-ponging
between 13.5 and 6.0 across rounds 6/8/9. The investigation already names both
contributing causes: hand-duplicated shared constants instead of a `joints` /
`mate_chain.py` derivation, and an unverified assumption about the resting plane.
Neither cause is detectable today because nothing ever asked "what is this correction
allowed to touch?"

The same gap explains the sibling item "Plan states that parts are pairwise mirrored"
(two identical files authored because the plan listed two ids) and the standing TODO
"user intent as invariant over the generation loops" -- there is currently no
invariant, only a log.

## Gap 3 -- the acceptance bar is plan-relative

The auditor agent deliberately receives the part's `BUILD_PLAN.json` entry and the
rendered views, and deliberately **not** the part script (so it cannot rationalize from
the code). But it also does not receive the `request_log`. The full chain is:

```
user request --(Phase 1-2)--> BUILD_PLAN.json --(Phase 3)--> script --> render
                                    ^                                     |
                                    +--------- audited against -----------+
```

Every gate downstream of Phase 2 measures conformance to the plan. If Phase 2 misread
the request, the misreading is the standard the rest of the pipeline enforces. This is
why `related_projects.md`'s cadgate row ("LLM-judge intent match is already covered by
the implementation audit") is only half true -- the audit judges the render against the
plan's intent, never against the words in `request_log`.

## Prior art worth adapting

| Work | What it is | Ideas worth adapting |
|------|-----------|---------------------|
| [ProCAD -- "Clarify Before You Draw"](https://arxiv.org/abs/2602.03045) (arXiv 2602.03045, 2026) | Proactive agentic text-to-CAD framework: a *clarifying agent* audits the prompt for under-specification and internal inconsistency and asks targeted questions **only when necessary**, paired with a CadQuery coding agent. Reports mean Chamfer distance down 79.9% and invalidity 4.8% -> 0.9% vs. frontier closed models, "keeping interaction overhead low" | Generalizes this skill's topology-clarification rule from shape to a full spec audit; the explicit ask-only-when-necessary budget matches the existing named-either/or-question discipline. Its coding agent is a fine-tune (not adoptable); the clarify stage is prompt-level and transfers as-is |
| [LLM4CAD-Editor](https://arxiv.org/abs/2606.20607) (arXiv 2606.20607, ASME IDETC-CIE 2026) | Intent-aware instruction-guided CAD editing over a DSL, modelling design intent at **three levels of abstraction: functional, operation, parameter**; feature-level entity selection lets instructions reference geometry by *name* instead of coordinates ("transforming coordinate-based reasoning into natural-language-based reasoning") | The three-level taxonomy is a ready-made vocabulary for typing `request_log` entries. The name-not-coordinate point is the same lesson as the standing `anchor()` / `place_at()` TODO item (offset to a body's tangent, not its center). The DSL and the 35k-pair fine-tuning dataset are not adoptable |
| [CADDesigner](https://arxiv.org/abs/2508.01031) (arXiv 2508.01031; CAD journal 2026) | General-purpose agent for conceptual CAD: an explicit **requirement-analysis dialogue** refines vague ideas into clear requirements before any code, then ReAct-style generation with symbolic + visual feedback | Confirms the Phase 1 / Phase 2 split retrospectively. Reusable part: treating requirement refinement as a named stage with an artifact, not as conversation that evaporates -- which is what a canonical restatement artifact would be here |
| [Ambiguity types in clarification generation](https://arxiv.org/pdf/2504.12113) (arXiv 2504.12113) | General NLP: prompting methods for clarification-question generation, measured per **ambiguity type** | Argues for an enumerated, named category list over a bare "ask if unsure" instruction -- directly shapes how the Phase 1 audit should be written |
| [CADialogue](https://github.com/Hiram31/CADialogue) (CAD journal 2025) | Multimodal LLM conversational assistant for parametric CAD; code released | Multi-turn intent tracking against a live parametric model; closest published analog to the mid-build correction problem. Worth reading before designing item 2 |
| [vericontext/cadgate](https://github.com/vericontext/cadgate) | Quality gate / PR reviewer for AI-generated CadQuery (already in `related_projects.md`) | Its LLM-judge **intent match** is the gap-3 item, not something already covered |
| [CadQuery-MCP `verify_cad_query`](https://github.com/rishigundakaram/cadquery-mcp-server) | Validator checking geometry against natural-language criteria (already tracked in `TODO.md` as optional-external) | Same mechanism as gap 3, arriving from the tool side rather than the gate side |

Deliberately excluded: [AutoConstrain / "Aligning Constraint Generation with Design
Intent in Parametric CAD"](https://arxiv.org/abs/2504.13178) -- 2D sketch-constraint
inference for editable sketches, a different meaning of "design intent" than the one
that matters here; and the IntentForge / LunaiCAD rows already rated Low in
`related_projects.md` (structured intent duplicating `BUILD_PLAN.json`, no new
mechanism).

## Adoptable items, ranked

Each item names where it lands and what it costs. Tracked in `TODO.md`.

### 1. Typed `request_log` entries (level + targets) -- strategy: reimplement

Add to each `request_log` entry a `level` (`functional` | `operation` | `parameter`,
per LLM4CAD-Editor) and `targets` (part ids plus named features / parameters the
utterance is about), assigned at append time by whoever appends.

Why first: it is the smallest change with the largest reach. It reuses the append-only
log, its schema, and `request_log_search.py`; it makes the C5 failure class expressible
as a rule ("a `parameter` entry targeting one part must not edit another part's literal
-- route a shared value through `joints` / `mate_chain.py`"); it gives the Step 3
section-selection tiers a better key than keyword matching; and it is the precondition
for items 2 and 3 being cheap.

Lands in: `src/build_plan_schema.json` (`request_log` items are
`additionalProperties: false`, so this is a schema change), `skill/phase3_build.md`'s
append rule, `prompts/planning.md` rule 14, `src/request_log_search.py` filters,
`tests/test_plan_validate.py` + `tests/test_request_log_search.py`,
`openspec/specs/request-log/`.

Watch out for: back-compat (existing plans have untyped entries -- the fields must be
optional, and absence must stay valid, same as `request_log` itself is optional today);
and resisting the urge to let the classifier *act* on its own label without the routing
rule that gives the label meaning.

### 2. Spec audit with named ambiguity categories -- strategy: reimplement (ProCAD)

Generalize the Phase 1 topology-clarification rule into an audit over a fixed category
list: topology (exists today), missing dimension, conflicting constraint, unstated
reference frame, unstated fit / load, part-vs-assembly scope. One question per
ambiguity found, keeping the existing either/or discipline, under a hard question
budget. Re-run the audit on a mid-build correction, not just on the initial request.

Lands in: `skill/phase1_requirements.md` (extends the existing clarification section
rather than adding a phase), `skill/phase3_build.md`'s correction handling.

Watch out for: over-asking. ProCAD's contribution is *only when necessary*; a rule that
fires on every request would be worse than today's. The budget and the "skip entirely
when nothing is ambiguous" escape hatch are load-bearing, exactly as the dimension
checkpoint's skip rule is.

### 3. Request-relative acceptance in the implementation audit -- strategy: reimplement (cadgate)

Give the auditor agent the `initial` `request_log` entry plus any entries whose
`targets` (item 1) name this part, as a **second** bar alongside the plan: "does this
render satisfy the user's own words?" Findings land in the existing `findings` array as
`severity: advisory` unless they also fail a checklist question.

Lands in: `skill/phase3_build.md` (Implementation audit prompt contents),
`reference/Visual Review Checklist.md` (a new question class),
`openspec/specs/subagent-orchestration/`.

Watch out for: false positives. Intent-match judgments are softer than geometry checks,
which is why advisory-by-default is the right severity -- promoting them to blocking
without eval evidence would burn retry budget on prose disagreements. Also keep the
existing no-script rule: the auditor still must not see the part script.

### 4. Canonical intent restatement as a durable artifact -- strategy: reimplement

The standing TODO items "intent based prompt reformulation" and "write a prompt which
allows the human user to re-generate the whole project from scratch with a new LLM
session" are the same artifact: a frame-explicit, user-confirmed restatement of what is
being built, carried forward and updated as corrections land. It is also the natural
input to item 3 and the structural fix for compass-language defects, since restatement
forces the reference frame to be written down instead of assumed.

Lands in: a new project-root artifact alongside `parameters.py` (provenance of
*measurements*) and `BUILD_PLAN.json` (structure), or an extension of one of them --
that choice is the design question, and it should not be answered by adding a third
free-text field to the plan.

Watch out for: overlap with `intent`, `planning_notes`, and `request_log`. The bounded
role of each is already carefully drawn (`planning_notes` is current-state-only,
`request_log` is history-only); a restatement artifact must be given an equally bounded
role or it will silently become a changelog.

### 5. Under-specified eval cases -- strategy: reimplement (gating cost, not optional)

Every case in `evals/cases/` is a well-specified request, so an intent-recognition
change has nothing to regress against and the existing scorecard (first-shot rate,
attempts-to-pass, Chamfer, cost/part) cannot see it. Needed: cases whose `request.md`
is deliberately under-specified in each named category, scored on whether the right
question was asked -- **and** well-specified controls scored on *not* asking. Without
the controls the metric rewards asking about everything.

Lands in: `evals/cases/`, `evals/run_evals.py` scoring, `tests/test_eval_corpus.py`.

## Caveats

- **Feature freeze.** `TODO.md` declares defects-only as of 12.08.2026. Items 1 and 3
  target logged, reproduced failures (C5 cradle; audit blind to the request) and are
  arguably defect fixes; 2, 4 and 5 are features. This document does not decide that.
- **An intent classifier is itself a failure mode.** Every item above is either a
  structured field with a validator or a prompt rule with a budget. None of them is
  "ask the model what the user meant" as an unchecked step, and the value of item 1
  comes from the routing rule attached to the label, not from the label.
- **Papers, not products.** ProCAD, LLM4CAD-Editor and CADDesigner are research; their
  fine-tuned models, DSLs and datasets are not adoptable here. The adoptable parts are
  the taxonomy, the clarify-then-generate ordering, and the ask-only-when-necessary
  budget -- all prompt-level.
- **Search coverage.** Surveyed 2026-08 via web search; arxiv.org and huggingface.co
  were unreachable from the session's egress proxy, so abstracts and mechanism details
  came from search summaries and secondary pages, not from reading the full PDFs. The
  numbers quoted for ProCAD are as reported in those summaries and should be re-checked
  against the paper before being cited anywhere load-bearing.

## Sources

- ProCAD -- Clarify Before You Draw: <https://arxiv.org/abs/2602.03045>
- LLM4CAD-Editor: <https://arxiv.org/abs/2606.20607>
- CADDesigner: <https://arxiv.org/abs/2508.01031>
- Ambiguity types in clarification generation: <https://arxiv.org/pdf/2504.12113>
- CADialogue: <https://github.com/Hiram31/CADialogue>
- AutoConstrain / design-intent constraint generation (excluded, for the record):
  <https://arxiv.org/abs/2504.13178>
