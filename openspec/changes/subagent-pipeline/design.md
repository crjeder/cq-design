# Design: sub-agent pipeline

## Context

Today the skill runs every phase inline: the main session reads the reference
corpus once, authors every part, reviews its own renders, and holds every
preview PNG and web-lookup snapshot for the life of the build. The harness
offers three primitives that change the calculus:

- **Agent tool** with a per-call `model` override and a free-text prompt - no
  `.claude/agents/` files required, so the skill stays portable.
- **Agent resume** (continue a previously spawned agent with its context
  intact) - enables hint-escalation without a cold respawn.
- **`claude -p` subprocess** - already used by `quality_gate.py` fixes and
  `evals/run_evals.py --generate`; the precedent for out-of-process LLM calls.

Two facts about the existing design make the split cheap:

1. `prompts/part.md` is rendered into a fully self-contained artifact (part
   entry, block specs, references, constraints all substituted in). It is
   already an agent prompt; nobody has been sending it to one.
2. `build/attempts.jsonl` already carries a `model` field per attempt and the
   eval harness already computes cost per accepted part from it - the
   measurement loop for model routing exists.

## Goals / Non-Goals

**Goals:**

- Main session context holds only: plan, checkpoint tables, verdicts, final
  preview paths. Render images and page snapshots are confined to the agents
  that consume them.
- Fresh-context implementation audit as the per-part acceptance bar.
- Per-role model routing (strong planner, cheaper builders), measured by the
  eval scorecard.
- Every user checkpoint stays in the main session, unchanged in content.

**Non-Goals:**

- No change to any `src/` script contract (wrapper JSON, gate stages,
  validators are untouched).
- No parallel builders in the first iteration - sequential per-part agents
  first; parallelism is a follow-up once telemetry append safety is verified.
- No `.claude/agents/` definitions shipped with the skill.
- Progressive build mode is not agentified - it is user dialog by definition.

## Decisions

1. **Agent boundaries = user-interaction x context-weight.** A role becomes an
   agent only if it (a) needs no mid-run user dialog and (b) consumes heavy
   context (images, web pages, reference corpus). That yields exactly four:
   research, planner, part builder, implementation auditor. Everything else
   (requirements Q&A, checkpoints, deterministic finish) stays in main.
   - Rejected: a "refine agent" separate from the drafter (the draft in
     `ARCHITECTURE.md`'s first version). It re-pays the reference tokens every
     round and loses attempt memory - the two things that make the current
     3-attempt loop effective.

2. **One builder agent per part, loop inside.** The builder owns
   write -> lint -> validate -> render -> self-check for max 3 attempts,
   appending one telemetry row per attempt. Return contract to main:
   `{part_id, status: passed|blocked, bbox, preview_paths, attempts, error_summary}`.
   No image content crosses the boundary - main displays previews from paths at
   the design-approval checkpoint.

3. **Blocked -> hint -> resume.** On `blocked`, main summarizes the errors,
   asks the user (hint / accept as-is / skip), and on a hint resumes the SAME
   agent. Respawning cold would discard exactly the attempt history the hint is
   meant to steer.

4. **Auditor never sees the script.** Input: the part's `BUILD_PLAN.json` entry
   + the preview/section/detail PNGs the builder produced. It answers the
   Visual Review Checklist questions with cited views and returns
   `{part_id, verdict, failed_questions: [{question, view, discrepancy}]}`.
   A failure re-enters the builder (resumed, so it knows its own history) as a
   targeted `visual_mismatch` fix. The builder keeps a light self-check so
   obviously-broken renders never reach the auditor.
   - Rejected: auditor replaces the deterministic checks - no; programs stay
     authoritative for geometry, the auditor only judges intent.

5. **Model routing defaults**: planner = strongest available (topology errors
   cost a full rebuild), builder = mid-tier (Sonnet-class), auditor/research =
   session default. Routing is a default, not a hard-coding - the SKILL text
   states the intent and the telemetry records what actually ran.

6. **Sequencing after `split-skill-md`.** The per-phase files it creates are
   the per-agent instruction sources: the builder agent prompt = rendered
   part prompt (unchanged), but the *orchestration* text that main follows
   lives in `skill/phase3_build.md`, which that change carves out. Doing this
   change first would mean editing SKILL.md text that is about to move.

7. **Cross-part pitfall injection (cheap carryover recovery).** Before
   spawning builder k, main scans this session's `attempts.jsonl` for repeated
   error types and prepends a one-line "known pitfalls this session" note to
   the rendered prompt. Bounded (a line or two), optional, and measurable.

## Risks / Trade-offs

- **Cold-start cost**: N builders x (pattern reference + anti-patterns + FDM
  guidelines) tokens vs. inline's one-time read plus image accumulation. The
  eval gate (cost per accepted part) decides; if agents lose on small models
  (1-2 parts), the routing gate can keep single-part builds inline.
- **Interface drift** between isolated builders of mating parts. Contract =
  the plan's `interfaces` entries; net = kinematic / plate-clearance /
  feature-presence checks. Watched explicitly in the first eval comparison.
- **Telemetry appends**: sequential builders are safe; parallelism deferred
  until append atomicity under concurrency is verified.
- **Auditor false negatives** (passing a wrong part): mitigated by keeping the
  user design-approval checkpoint unchanged and `feature_presence_check.py`
  in the gate.

## Open Questions

- Does the research agent pay for itself on requests with no real-world
  product lookup? (Routing: only spawn it when a lookup is actually needed -
  same condition that gates the dimension checkpoint today.)
- Should the auditor also run for progressively built parts (fresh eyes after
  the user already approved each stage)? Current answer: yes, same bar, cheap.
- Parallel builders: worth it beyond ~3 parts, blocked on telemetry
  concurrency check.
