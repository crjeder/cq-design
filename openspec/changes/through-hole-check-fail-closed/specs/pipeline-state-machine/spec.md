## ADDED Requirements

### Requirement: Plan approval records planned through-hole counts

`pipeline.py advance phase2/plan_approved` SHALL append `b1=<part_id>:<n>[,<part_id>:<n>...]`
to the journal text when the text does not already contain `b1=`. `<n>` is the sum of
`through_count` over that part's interfaces in `BUILD_PLAN.json`. A part SHALL be listed
when at least one of its interfaces declares `through_count`, or when the plan's
`design_intent` is `"cad"` (missing values counted as 0). `b1=` SHALL be omitted when no
part qualifies. `pipeline.py status` SHALL report the latest valid `plan_approved` line's
record as `approved_b1` (an object from part id to integer, empty when absent).

#### Scenario: CAD plan with mixed declarations
- **WHEN** a `design_intent: "cad"` plan has part `block` with interfaces at
  `through_count` 1, 1 and one without the field, and `advance phase2/plan_approved "ok"`
  is run
- **THEN** the journal line reads `- phase2/plan_approved: ok b1=block:2`

#### Scenario: Print plan with no declarations
- **WHEN** a `design_intent: "print"` plan declares no `through_count`
- **THEN** the appended line has no `b1=` and `status` reports `approved_b1: {}`

#### Scenario: Re-approval replaces the record
- **WHEN** the journal has `plan_approved ... b1=elbow:9` and later `plan_approved ...
  b1=elbow:6`
- **THEN** `status` reports `approved_b1: {"elbow": 6}`, and every `part_accepted:elbow`
  line between the two is listed under `void`
