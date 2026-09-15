## MODIFIED Requirements

### Requirement: Fresh-context implementation audit
A part accepted by its builder SHALL be judged by an auditor agent that
receives the part's `BUILD_PLAN.json` entry, the rendered preview, section, and
detail images, and the scoped `request_log` text (the `initial` entry plus every
entry whose typed `targets` name this part, or absent typed targets every entry
matched by `request_log_search.py --query <part id or name>`). It SHALL NOT
receive the part script. The auditor answers the Visual Review Checklist
questions, each against a specific cited view, AND judges whether the render
satisfies the fed request wording as a second, advisory bar. An audit failure
re-enters that part's builder as a targeted `visual_mismatch` fix.

#### Scenario: Auditor input isolation
- **WHEN** the auditor agent is spawned for a part
- **THEN** its prompt contains the plan entry, the image paths, and the scoped
  `request_log` text but no part script source

#### Scenario: Audit failure
- **WHEN** the auditor answers any checklist question "no"
- **THEN** it names the question, the cited view, and the discrepancy, and the
  part's builder is resumed with that finding

#### Scenario: Request-conformance finding is advisory
- **WHEN** the auditor judges the render contradicts the fed request wording but
  every checklist question still answers "yes"
- **THEN** the audit verdict is `pass`, an advisory finding naming the contradicted
  request text and its cited view is returned in `findings`, and it is surfaced to
  the user without resuming the builder

#### Scenario: Request contradiction that also fails a checklist question
- **WHEN** the discrepancy that contradicts the request wording also answers a
  checklist question "no"
- **THEN** it is returned in `failed_questions` as `severity: blocking` with the
  request text cited as supporting evidence, and the builder is resumed
