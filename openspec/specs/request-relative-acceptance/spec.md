# request-relative-acceptance

## Purpose

Defines a second acceptance bar for part reviews: in addition to conformance to
the part's `BUILD_PLAN.json` entry, every review measures the delivered render
against the user's own request wording taken verbatim from `request_log`. It sets
the advisory-vs-blocking rule for the resulting intent-match findings, preserves
the auditor no-script rule, and gates any future promotion of these findings to
blocking on eval evidence.

## Requirements

### Requirement: The review measures the render against the user's own words

Every part review -- the progressive-mode visual self-review and the fresh-context
implementation audit -- SHALL evaluate the delivered render against the user's
request as a second acceptance bar, in addition to the existing bar of conformance
to the part's `BUILD_PLAN.json` entry. The request text SHALL be taken from the
plan's approved `intent` (the user-approved reformulation, per the `approved-intent`
spec), plus every `request_log` entry scoped to the part under review. An entry is
scoped to the part when its typed `targets` name the part (once typed `request_log`
entries exist) or, absent typed targets, when `log.py request search --query <part id
or name>` matches it.

`intent` replaces `request_log`'s `initial` entry as the global reference frame for
this bar: the `initial` entry holds the user's unresolved wording, while `intent`
holds the reading the user approved. When a plan carries no `intent` long enough to
be a reformulation -- an eval-corpus golden, or a plan predating this rule -- the
`initial` entry SHALL be used in its place if one exists.

#### Scenario: Plan misread the request

- **WHEN** a part's `BUILD_PLAN.json` entry places a feature on a face that
  contradicts the approved `intent`, and the render faithfully matches that
  plan entry
- **THEN** the review records a request-conformance finding naming the contradicted
  intent text and the cited view, even though every plan-conformance question
  passes

#### Scenario: Render satisfies both bars

- **WHEN** the render matches the plan entry and neither the approved `intent` nor any
  scoped `request_log` entry contradicts what the render shows
- **THEN** no request-conformance finding is recorded

#### Scenario: Render contradicts a stated assumption

- **WHEN** `intent` records "legs 24 mm to start -- assumed" and the render shows legs
  at a materially different length with no correction entry explaining it
- **THEN** the review records a request-conformance finding citing that assumption

#### Scenario: Legacy plan without a reformulated intent

- **WHEN** a plan's `intent` is a short pre-reformulation description and a
  `request_log` `initial` entry exists
- **THEN** the bar is fed the `initial` entry as before, plus the scoped entries

#### Scenario: No intent and no request_log present

- **WHEN** a plan carries neither an approved `intent` nor a `request_log` (for example
  an eval-corpus golden plan)
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

### Requirement: Visual oracle statements are blocking checklist questions

When `acceptance.json` exists, every `visual` statement bound to the part under review (or
bound to `"*"`) SHALL be added to that review's Visual Review Checklist as a question
labelled with its statement id and `text`. Both the progressive self-review and the
implementation audit SHALL answer it. A "no" SHALL be recorded as a blocking
`visual_mismatch` naming the statement id and the cited view, and SHALL take part in the
existing retry budget. A statement still answered "no" after 3 rounds SHALL be escalated
to the user with the same choices as an `oracle_unmet` escalation. This requirement does
not change the advisory severity of the free-form request-conformance finding.

#### Scenario: Visual statement fails review

- **WHEN** `S7` "rounded, friendly look" is bound to the part and the auditor answers it
  "no" citing the iso view
- **THEN** a blocking `visual_mismatch` naming `S7` and the iso view is recorded and the
  builder is resumed with it

#### Scenario: Free-form finding stays advisory

- **WHEN** the reviewer also notes a request-conformance discrepancy not covered by any
  statement or checklist question
- **THEN** it is recorded as advisory, as before

#### Scenario: Auditor input still excludes the script

- **WHEN** the audit prompt is rendered with visual statements added
- **THEN** it contains the statement texts and no part script source
