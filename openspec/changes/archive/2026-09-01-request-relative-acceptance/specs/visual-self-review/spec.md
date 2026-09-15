## ADDED Requirements

### Requirement: The progressive review checks the render against the user's own words

During the progressive-mode Phase 3 part loop, the question-driven visual
self-review SHALL include a request-conformance question class in addition to the
plan-derived questions and the universal invariants. The questions SHALL be
generated from the scoped `request_log` text for the part (the `initial` entry plus
every entry `request_log_search.py --query <part id or name>` matches, or entries
whose typed `targets` name the part once those exist), each answered against a
specific cited view. When `BUILD_PLAN.json` carries no `request_log`, this question
class is omitted and the review proceeds unchanged.

#### Scenario: Request-conformance question generated

- **WHEN** an inline part is reviewed and its scoped `request_log` text names a
  feature placement or form
- **THEN** the review includes a yes/no question checking the render against that
  wording, answered against a cited view

#### Scenario: No request_log

- **WHEN** the plan has no `request_log`
- **THEN** no request-conformance questions are generated and the plan-derived
  questions and universal invariants are unaffected

### Requirement: Request-conformance mismatches follow the advisory-vs-blocking rule

A request-conformance question answered "no" SHALL be recorded as an advisory
finding -- reported and displayed to the user, but not failing the review, not
consuming a retry attempt, and not folded into a targeted fix prompt -- UNLESS the
same discrepancy also answers a plan-derived question or universal invariant "no",
in which case it is a blocking `visual_mismatch` exactly as today, with the request
text cited as supporting evidence.

#### Scenario: Request mismatch, all other questions pass

- **WHEN** a request-conformance question answers "no" and every plan-derived
  question and universal invariant answers "yes"
- **THEN** an advisory finding is recorded with its cited view, the part is marked
  done, and no retry is consumed

#### Scenario: Request mismatch that also fails a plan question

- **WHEN** the discrepancy also answers a plan-derived question or universal
  invariant "no"
- **THEN** a blocking `visual_mismatch` is recorded citing both the failed question
  and the contradicted request text, and it participates in the retry budget
