## Why

Every gate downstream of Phase 2 measures the part against `BUILD_PLAN.json`, never
against the user's own words. The auditor agent is deliberately given the plan entry
and renders but not the script -- and also not the `request_log` -- so a Phase 2
misreading of the request becomes the standard the whole pipeline enforces, and no
gate can catch it. Logged failure: the C5 phone-holder cradle, where the plan
encoded a wrong reference frame and every gate passed it.

## What Changes

- The implementation auditor prompt gains a SECOND acceptance bar: the `initial`
  `request_log` entry plus any entries scoped to the part under review, and the
  question "does the render satisfy the user's own words?"
- The progressive-build visual self-review gains the same bar for inline parts.
- `reference/Visual Review Checklist.md` gains a request-conformance question class,
  generated from the fed `request_log` text, answered against a cited view.
- Intent-match findings are recorded at `severity: advisory` -- reported and
  surfaced, never blocking and never folded into a fix prompt -- UNLESS the same
  discrepancy also fails an existing checklist question, in which case it stays
  blocking exactly as today.
- The no-script rule for the auditor is unchanged; only `request_log` text is added
  to its input.
- No new agent, no new artifact, no schema change.

## Capabilities

### New Capabilities
- `request-relative-acceptance`: the review measures the delivered render against the
  user's original request wording as a second, advisory bar, alongside the existing
  plan-conformance bar -- so a plan that misread the request is caught instead of
  enforced.

### Modified Capabilities
- `subagent-orchestration`: the fresh-context implementation auditor's input gains
  the scoped `request_log` text and its checklist gains the request-conformance
  question class; audit-failure semantics clarified for advisory intent-match findings.
- `visual-self-review`: the progressive-mode part loop review applies the same
  request-conformance question class with the same advisory-vs-blocking rule.

## Impact

- `skill/phase3_build.md` -- Implementation audit section (auditor prompt contents,
  return-contract handling) and progressive Step 4 review.
- `reference/Visual Review Checklist.md` -- new question class.
- `src/request_log_search.py` -- used to select the entries fed to the auditor
  (already exists; may need a part-scoping helper if typed `targets` are absent).
- `evals/` -- adoption is gated on the under-specified eval cases; intent-match
  findings do not ship as blocking without eval evidence.
- No change to `run_cadquery_model.py`, `build_plan_schema.json`, or the auditor
  no-script rule.

## Out of Scope

- Adding deliberately under-specified eval cases (`evals/cases/`) -- tracked as
  intent-recognition survey item 5.
- Promoting request-conformance findings from advisory to blocking -- gated on the
  eval evidence above.
- Typed `request_log` `level`/`targets` fields -- intent-recognition survey item 1.
