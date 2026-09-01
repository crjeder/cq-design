## MODIFIED Requirements

### Requirement: The review measures the render against the user's own words

Every part review -- the progressive-mode visual self-review and the fresh-context
implementation audit -- SHALL evaluate the delivered render against the user's
request as a second acceptance bar, in addition to the existing bar of conformance
to the part's `BUILD_PLAN.json` entry. The request text SHALL be taken from the
plan's approved `intent` (the user-approved reformulation, per the `approved-intent`
spec), plus every `request_log` entry scoped to the part under review. An entry is
scoped to the part when its typed `targets` name the part (once typed `request_log`
entries exist) or, absent typed targets, when `request_log_search.py --query <part id
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
