## Context

The cq-design pipeline preserves the user's request verbatim in
`BUILD_PLAN.json`'s `request_log` (capability `request-log`), but no gate after
Phase 2 reads it. The fresh-context implementation auditor
(`subagent-orchestration`) and the progressive visual self-review
(`visual-self-review`) both judge a part against its `BUILD_PLAN.json` entry and
the renders. The auditor is deliberately denied the part script so it cannot
rationalize from the code -- but it is also denied the request, so a Phase 2
misreading is invisible: the plan becomes the enforced truth.

Logged failure: the C5 phone-holder cradle
(`session-export-1786538430013.zip`). The triggering request was a folded-pose
constraint ("align the hole with the bore hole ... when the leg lies flat on the
front plate"); the plan encoded independent pivot literals in the wrong frame;
every gate passed. The compass-language defect (east/right confusion from
"viewed from South" vs "south facing") is the same class -- an unstated reference
frame that only the original wording pins down.

TODO item: intent-recognition survey #3, `documentation/intent_recognition.md`.
The freeze note (12.08.2026) flags this as arguably a V1 defect fix.

## Goals / Non-Goals

**Goals:**
- Give the auditor and the progressive review a second bar: "does the render
  satisfy the user's own words?", fed from `request_log`.
- Catch plan-vs-request divergence without a new agent, artifact, or schema field.
- Keep the auditor's no-script rule intact.
- Ship intent-match findings as advisory-only; do not burn retry budget on soft
  judgments.

**Non-Goals:**
- Typed `request_log` `level`/`targets` fields -- separate change; this one
  degrades to keyword scoping until they exist.
- Promoting intent-match findings to blocking -- gated on eval evidence, not in
  this change.
- A canonical intent restatement artifact -- separate TODO item.
- Feeding the request to the builder or to deterministic checks -- review only.
- Re-auditing Phase 1 clarification quality -- that is the spec-audit item.

## Decisions

### Feed `request_log` text, not a new "intent" artifact
The request wording already exists verbatim and is carried forward across
re-plans. Adding it to the review prompt is a one-file input change. Alternative
(a synthesized intent restatement) is a separate TODO item with its own
storage/role questions; not a prerequisite here.

### Scope entries to the part by keyword match now, typed targets later
The clean selector is `request_log` entries whose typed `targets` name the part,
but that field does not exist yet. `request_log_search.py --query <part id or
name>` already exists and gives a usable approximation. The spec is written so the
typed-targets path supersedes the keyword path transparently when it lands. The
`initial` entry is always fed regardless of scoping -- it holds the global frame.

### Advisory by default, blocking only via an existing checklist question
Intent-match is a softer judgment than geometry conformance and burns retry
budget if wrong. The `visual-self-review` capability already has the
advisory-vs-blocking machinery (coverage-first rule: the review reports
everything, the fix decision filters). Request-conformance findings reuse it
exactly. A discrepancy that also fails a plan question was already blocking; it
stays blocking and simply cites the request text as extra evidence.

### Same rule in both review paths
Progressive (inline, `visual-self-review`) and autonomous (auditor,
`subagent-orchestration`) must not diverge, or a part's acceptance bar would
depend on its routing. Both get the question class and the same severity rule.

### Eval-gate the promotion, not the feature
The feature (advisory findings) is low-risk and ships now. Making the findings
blocking is the risky part and is deferred behind under-specified eval cases
(intent-recognition survey #5), consistent with `subagent-orchestration`'s
existing "adoption is eval-gated" requirement.

## Risks / Trade-offs

- [Reviewer over-reports on verbose requests, flooding the user with advisories]
  → advisories are grouped separately from failed questions and never block;
  checklist wording caps it at "wording the render visibly contradicts", not
  every unmet nicety.
- [Keyword scoping misses an entry that names the part obliquely] → the `initial`
  entry is always fed, so the global frame is never missed; per-part corrections
  that don't mention the part id are the residual gap, closed by typed targets
  later.
- [Advisory findings get ignored and the misread still ships] → accepted; this
  change surfaces the divergence to the user at the Design approval checkpoint,
  which is where a human can catch it. Blocking enforcement is a later,
  eval-gated step.
- [Two review paths drift over time] → the question class and severity rule live
  in one place, `reference/Visual Review Checklist.md`; both paths cite it.

## Migration Plan

1. Add the request-conformance question class to
   `reference/Visual Review Checklist.md` with the advisory-vs-blocking rule and
   the "promotion needs eval evidence" note.
2. Update `skill/phase3_build.md` Implementation audit section: add scoped
   `request_log` text to the auditor prompt contents; document the advisory
   finding in the return-contract handling.
3. Update `skill/phase3_build.md` progressive Step 4: add the question class to
   the inline review.
4. Add a part-scoping helper to `request_log_search.py` only if the existing
   `--query` is insufficient.
5. Add/refresh eval cases (deferred to the under-specified-eval-cases item) before
   any promotion to blocking.

Rollback: revert the checklist and `phase3_build.md` edits; no data or schema
migration.

## Open Questions

- Does `request_log_search.py --query` need a dedicated `--part` mode, or is
  passing the part id/name/description as the query string enough in practice?
- Should the `initial` entry be fed whole, or trimmed to the sentences a
  lightweight relevance pass keeps? (Default: whole -- it is short and the frame
  is often in an aside.)
