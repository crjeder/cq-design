## Context

Three verification layers overlap today, each added when 4.x-era models needed
the scaffolding:

- **Gate auto-fix.** `run_gate(allow_fix=True)` is the default (`src/quality_gate.py:499`)
  and the CLI opts *out* via `--no-fix` (line 634). `skill/phase3_build.md`'s
  Quality gate invocation passes neither flag, so today every gate run in the
  real pipeline can silently rewrite the part script from a cold `claude -p`
  subprocess that has only the fix prompt — no plan, no render, no attempt
  history, no `cq_verify` context. Every existing test already passes
  `allow_fix=False` explicitly, so no test depends on the current default.
- **Checklist filtering.** `reference/Visual Review Checklist.md` is
  question-driven with a binary answer per question; the only reporting channel
  for something the reviewer noticed but is unsure about is silence. On 5-series
  models a severity filter inside the review prompt suppresses reporting, not
  just escalation.
- **Builder self-check.** `phase3_build.md` Step 4's autonomous branch runs a
  "light self-check" scan of the render, and the same file (line 429) already
  says `status: passed` is *not* acceptance — the fresh-context auditor is. The
  self-check is the model reviewing its own output immediately before a reviewer
  that never saw the script does it properly.

C4's acceptance criterion is the eval harness, compared against the C2/C3 runs
(`evals/runs/c2-prompt-chars/`, `evals/runs/c3-planning/`), not inspection.

## Goals / Non-Goals

**Goals:**
- The gate never mutates a part script unless the caller explicitly asked for it.
- Gate findings reach a fixer that has the part's full context.
- The visual review reports everything it observes; the pass/fail decision
  filters afterwards.
- One model-driven review per part in the autonomous path, not two.

**Non-Goals:**
- Changing which findings block. Severity assignment (`error` vs `warning`) and
  the gate's exit code / `passed` semantics stay exactly as they are.
- Touching the deterministic checks (lint, wrapper DFM, kinematic,
  plate-clearance, keep-out, edge-treatment, feature-presence). They are
  programs; the "delete verification scaffolding" guidance is about prompts.
- Removing `_call_claude` / `_render_fix_prompt`. They remain reachable via
  `--fix` and are needed again by C6 (`--model` plumbing).
- The progressive (inline) path's full question-driven review. That is a user-
  facing checkpoint, not model self-verification.

## Decisions

**D1. Invert the flag rather than add `--report-only`.** `--no-fix` is replaced
by `--fix`; `allow_fix` defaults to `False`. Keeping `--no-fix` as a deprecated
alias was rejected: the only in-repo caller is `phase3_build.md` (which passes
neither), the tests all pass the kwarg explicitly, and a silent alias would let a
stale copy of the skill keep auto-fixing while reading as opted-out. A hard flip
surfaces any stale caller immediately as an unrecognized-argument error.

**D2. Findings route to the caller, not to a subprocess.** `phase3_build.md`'s
Quality gate section gains an explicit instruction: parse
`build/quality_gate.json`, and on any `severity: error` re-enter the part loop's
fix path (Step 2) for the offending part's script with the finding's
`type`/`message`/`hint` as the correction, then re-run the gate. This is the same
mechanism the wrapper's typed errors already use — the gate stops being a
special case with its own fixer. Alternative considered: have the gate emit a
fix prompt file for the caller to feed to an agent. Rejected as a second prompt
surface for the same job the part loop already does with more context.

**D3. Gate re-run budget mirrors the part loop, not `MAX_FIX_ROUNDS`.** With
`allow_fix` off, `MAX_FIX_ROUNDS` and the internal `for fix_round` loop become
dead in the default path (the loop still breaks out on the first clean pass, and
`fix_rounds` stays in the report for `--fix` runs). The bound on gate-driven
fixes moves to the skill file: at most 2 gate-fix rounds per part, matching the
old `MAX_FIX_ROUNDS`, so the change is cost-neutral rather than unbounded.

**D4. Coverage-first is a Rules-section change, not a restructure.** The
question bank, view-citation rule, and engineering rows are unchanged — they are
elicitation structure, not filtering. What changes is the reporting contract in
the Rules section and the two return contracts that carry review output
(`failed_questions` in the Implementation audit gains `confidence` and
`severity`, and gains entries that do not fail the part). A finding with
`severity: advisory` is reported and displayed but does not by itself block
acceptance — so recall rises without the retry budget rising.

**D5. The builder returns after deterministic checks only.** Step 4's autonomous
branch drops the self-check scan entirely; a builder that passed lint, wrapper
validation, and rendering returns `status: passed` with its preview paths. The
"something obviously broken" retry branch goes with it — a genuinely broken
render is either caught by the wrapper (`disconnected_body`, `dimension_mismatch`)
or by the auditor, which then resumes the same builder with a named finding. The
builder's 3-attempt budget is unchanged; it is now spent only on typed errors and
auditor findings.

**D6. Blast radius of `visual_mismatch` is unchanged.** The finding type, its
place in the retry budget, and its telemetry field (`visual_review.failed_question`)
stay. Coverage-first adds sibling advisory findings; it does not rename or
re-type the blocking one.

## Risks / Trade-offs

- **Coverage-first floods the checkpoint with noise.** → Advisory findings are
  reported but grouped separately from the ones that fail a question, and the
  progressive checkpoint displays them under a distinct heading. If the eval
  sweep shows attempts-to-pass rising, the mitigation is to keep advisory
  findings out of the fix prompt (report to the user, do not act), not to
  reinstate the filter.
- **Dropping the builder self-check lets an obviously broken render reach the
  auditor**, costing one extra audit round-trip. → That is the intended trade:
  one auditor call replaces one self-check plus a (frequently redundant) auditor
  call. Watch cost per accepted part in the sweep; the wrapper's typed errors
  still catch the structurally broken cases before any render is judged.
- **Gate findings now need a human/orchestrator in the loop.** A fully
  unattended `quality_gate.py` invocation that used to self-heal will now just
  report and exit non-zero. → `--fix` restores the old behavior for anyone
  scripting the gate outside the skill, and `phase3_build.md` gains the explicit
  routing so the pipeline itself does not regress.
- **Two behavior changes plus a prompt change in one eval sweep** cannot be
  attributed individually if the scorecard moves. → Accepted: C4's acceptance
  gate is "improve or hold" against C2/C3, not attribution. C2's own result
  section already documents that run-to-run spread exceeds the per-change
  effect, so splitting into three sweeps would not buy attribution anyway.
