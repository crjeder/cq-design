## ADDED Requirements

### Requirement: The review measures the render against the user's own words

Every part review -- the progressive-mode visual self-review and the fresh-context
implementation audit -- SHALL evaluate the delivered render against the user's
original request wording as a second acceptance bar, in addition to the existing
bar of conformance to the part's `BUILD_PLAN.json` entry. The request wording SHALL
be taken verbatim from `request_log`: the single `initial` entry, plus every entry
scoped to the part under review. An entry is scoped to the part when its typed
`targets` name the part (once typed `request_log` entries exist) or, absent typed
targets, when `request_log_search.py --query <part id or name>` matches it.

#### Scenario: Plan misread the request

- **WHEN** a part's `BUILD_PLAN.json` entry places a feature on a face that
  contradicts the `initial` request wording, and the render faithfully matches that
  plan entry
- **THEN** the review records a request-conformance finding naming the contradicted
  request text and the cited view, even though every plan-conformance question
  passes

#### Scenario: Render satisfies both bars

- **WHEN** the render matches the plan entry and no fed `request_log` text
  contradicts what the render shows
- **THEN** no request-conformance finding is recorded

#### Scenario: No request_log present

- **WHEN** `BUILD_PLAN.json` carries no `request_log` (for example an eval-corpus
  golden plan)
- **THEN** the request-conformance bar is skipped and the review proceeds on the
  plan-conformance bar alone

### Requirement: Intent-match findings are advisory unless they also fail a checklist question

A request-conformance finding SHALL be recorded at `severity: advisory`: it is
reported to the user and surfaced alongside the accepted part, but it SHALL NOT by
itself fail the review, consume a retry attempt, or be folded into a targeted fix
prompt. When the same discrepancy also answers an existing Visual Review Checklist
question "no", it SHALL be recorded as a blocking `visual_mismatch` exactly as
today, and the request text SHALL be cited in that finding as supporting evidence.

#### Scenario: Intent mismatch with all checklist questions passing

- **WHEN** the reviewer judges the render contradicts the fed request wording, but
  every checklist question still answers "yes"
- **THEN** an advisory request-conformance finding is recorded with its cited view,
  the part passes the review, and no retry is consumed

#### Scenario: Intent mismatch that also fails a checklist question

- **WHEN** the discrepancy that contradicts the request wording also answers a
  checklist question "no"
- **THEN** a blocking `visual_mismatch` is recorded naming that question and its
  view, the request text is cited as supporting evidence, and it participates in
  the retry budget as before

### Requirement: The auditor no-script rule is preserved

Adding `request_log` text to a review's input SHALL NOT relax the rule that the
implementation auditor receives no part script. The auditor's input gains only the
verbatim request text; it still judges the render against the plan and the request
with no access to the code that produced the geometry.

#### Scenario: Auditor input after the change

- **WHEN** an auditor agent is spawned for a part
- **THEN** its prompt contains the part's `BUILD_PLAN.json` entry, the image paths,
  and the scoped `request_log` text -- and no part script source

### Requirement: Promotion of intent-match findings to blocking is eval-gated

Request-conformance findings SHALL NOT be made blocking by default. Any future
change that promotes them to blocking SHALL first be justified by
`evals/run_evals.py` evidence from under-specified eval cases, showing the
promotion catches real misreads without a net increase in wasted retries.

#### Scenario: Default severity

- **WHEN** this change ships
- **THEN** request-conformance findings are advisory-only, and the checklist and
  `skill/phase3_build.md` state that promoting them requires eval evidence
