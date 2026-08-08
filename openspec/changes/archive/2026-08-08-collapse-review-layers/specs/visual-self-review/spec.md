## ADDED Requirements

### Requirement: The review reports every observed discrepancy, not only failing answers

The visual review SHALL report every discrepancy it observes, each carrying a
confidence and a severity, and SHALL NOT withhold an observation because it is
low-confidence or judged minor. The checklist SHALL state that the fix decision
filters findings, not the review. A finding recorded as advisory SHALL be
reported and displayed but SHALL NOT by itself fail a question or consume a
retry attempt; a finding that answers a checklist question "no" remains a
blocking `visual_mismatch` exactly as before.

#### Scenario: Low-confidence observation is still reported

- **WHEN** the reviewer notices a possible discrepancy it is not confident about,
  and every checklist question still answers "yes"
- **THEN** the discrepancy is recorded as an advisory finding with its confidence
  and severity, the part still passes the review, and no retry is consumed

#### Scenario: Advisory findings are surfaced

- **WHEN** a part passes its review with one or more advisory findings
- **THEN** they are displayed to the user alongside the reviewed views, grouped
  separately from any failed question

#### Scenario: Blocking semantics unchanged

- **WHEN** a checklist question is answered "no"
- **THEN** a `visual_mismatch` finding naming that question, its cited view, and
  the discrepancy is recorded, and it participates in the retry budget as before

#### Scenario: Advisory findings stay out of the fix prompt

- **WHEN** a targeted fix is driven by a failed question
- **THEN** the correction addresses the failed question, and advisory findings are
  not folded into it as additional work
