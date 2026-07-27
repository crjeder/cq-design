# Visual Self-Review (delta)

## ADDED Requirements

### Requirement: Numbers-demanding engineering rows for load-bearing parts

The review question bank SHALL include an engineering row class, generated for parts
that meet the engineering-rationale trigger (a declared plan `load`, or load-bearing
blocks/archetype). Each engineering row SHALL demand a value and its threshold - e.g.
"What is rib thickness / wall thickness? Is it <= 0.6?", "What is the snap-arm strain
at full deflection vs. the material allowable?" - rather than a judgment question.
Engineering rows SHALL be answered by citing the script's PARAMETERS values, its
ENGINEERING RATIONALE block, or the wrapper's `geometry` JSON (not a rendered view);
the checklist SHALL state explicitly that the view-citation rule applies to visual
rows only, and that numeric rows cite the parameter or geometry value the number came
from. An engineering row whose re-derived value contradicts the script's rationale
block, or exceeds its threshold, SHALL be a recorded finding that blocks the pass,
like any failed question.

#### Scenario: Ribbed load-bearing part

- **WHEN** a part with ribs and a declared load is reviewed
- **THEN** the questions include a rib-thickness-to-wall ratio row answered with the
  actual parameter values and the <= 0.6 threshold, citing the parameters used

#### Scenario: Rationale contradicted at review

- **WHEN** re-deriving an engineering row's value from the script's parameters gives
  a result that exceeds the stated allowable, though the rationale block claimed it
  passed
- **THEN** the review records a finding naming the row and the discrepancy, and the
  part is not passed on that attempt

#### Scenario: Non-load-bearing part

- **WHEN** a part that does not meet the engineering-rationale trigger is reviewed
- **THEN** no engineering rows are generated for it and the visual rows are
  unaffected
