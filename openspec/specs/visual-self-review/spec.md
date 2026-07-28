# Visual Self-Review

## Purpose

Defines requirements for a visual self-review step in the Phase 3 part loop, where Claude inspects each rendered preview against design intent (via a structured checklist) before a part is marked done, records `visual_mismatch` findings, and surfaces review outcomes to the user.
## Requirements
### Requirement: Part loop performs a visual self-review before a part is marked done

During the Phase 3 part loop, after a part passes geometry validation and a preview PNG is produced, Claude SHALL visually inspect the rendered preview against the design intent before marking the part done. A part SHALL only be considered done when geometry validation passes AND the visual self-review confirms the render matches intent.

#### Scenario: Geometry passes and render matches intent
- **WHEN** `run_cadquery_model.py` returns `success: true` with no blocking errors and a preview PNG, and the visual self-review finds no mismatch
- **THEN** the part is marked done, its `geometry.bbox` is recorded, and the loop advances to the next part

#### Scenario: Geometry passes but render does not match intent
- **WHEN** geometry validation passes but the visual self-review finds the render does not match the design intent (wrong shape, missing or misplaced feature, mirrored cutout, wrong proportions)
- **THEN** the part is NOT marked done, a `visual_mismatch` finding describing the discrepancy is recorded, and (if the attempt budget is not exhausted) the loop retries with a targeted fix driven by that description

#### Scenario: Geometry fails
- **WHEN** geometry validation returns a blocking error
- **THEN** the geometry error is handled first and the visual self-review is skipped for that attempt

### Requirement: visual_mismatch is a documented loop finding

The `visual_mismatch` finding SHALL be documented in the SKILL error-handling reference with its meaning and corrective action. It SHALL be recorded by Claude within the part loop and SHALL participate in the same retry budget as geometry errors. It SHALL NOT be emitted by `run_cadquery_model.py` (the wrapper JSON contract is unchanged).

#### Scenario: visual_mismatch documented in error reference
- **WHEN** a reader consults the SKILL error-handling reference table
- **THEN** `visual_mismatch` appears with its meaning and the corrective action (re-examine intent, fix the responsible parameter or geometry)

#### Scenario: Wrapper contract unchanged
- **WHEN** `run_cadquery_model.py` runs a model
- **THEN** its JSON output keys and error types are unchanged and contain no `visual_mismatch` entry

### Requirement: Visual review outcome is surfaced to the user

When a part is marked done, Claude SHALL display the reviewed preview PNG. When the attempt budget is exhausted with an unresolved `visual_mismatch`, Claude SHALL summarize the remaining mismatch to the user and ask conversationally how to proceed (provide a hint, accept as-is, or skip the part).

#### Scenario: Done part shows its preview
- **WHEN** a part is marked done
- **THEN** the reviewed preview PNG is displayed to the user

#### Scenario: Unresolved mismatch after retries
- **WHEN** the attempt budget is exhausted and a `visual_mismatch` remains
- **THEN** Claude summarizes the mismatch and asks the user how to proceed

### Requirement: Every verification answer cites the view it was judged from

Each verification question SHALL be answered against a specific rendered view (an
orthographic panel, the isometric, or a named section file), and the answer SHALL cite
that view. When no already-rendered view shows the geometry a question is about (for
example an internal feature or a body junction with no section through it), Claude
SHALL render the needed section or detail view before answering. An answer that cannot
cite a view actually showing the relevant geometry SHALL NOT count as a pass.

#### Scenario: Answer cites a view

- **WHEN** a question about a top-face boss is answered
- **THEN** the answer cites the Top panel (or a section/detail through the boss) as the
  view it was judged from

#### Scenario: Missing view is rendered before answering

- **WHEN** a question concerns an internal feature and no rendered section crosses it
- **THEN** the required section is rendered first and the answer cites that section;
  the question is not passed on an uncitable answer

### Requirement: Connectedness is a mandatory invariant answered against sections

The single-connected-body invariant SHALL always be evaluated, and SHALL be answered
against section views that cross the part's body junctions -- not exterior or isometric
panels alone, which can overlap in projection and read as connected when they are not.
This visual invariant is complementary to the deterministic `disconnected_body`
wrapper error: the wrapper error is the blocking gate, and the invariant is the
human-legible cross-check that also covers bodies which touch without fusing.

#### Scenario: Disconnection visible only in section

- **WHEN** a part that must be one body renders as separate solids that overlap in the
  exterior projection
- **THEN** the connectedness invariant is answered against a section crossing the
  junction, the answer is "no", and a `visual_mismatch` is recorded

#### Scenario: Connectedness invariant runs for every part

- **WHEN** any part is reviewed
- **THEN** the single-connected-body invariant is among the evaluated questions,
  regardless of the part's declared features

### Requirement: Review-input artifacts are not overwritten before the review reads them

The review SHALL read the rendered files it depends on -- the default tile and its
section/detail files for the attempt under review -- before any subsequent render can
overwrite them. The renderer SHALL write to stable per-part names and the loop SHALL
consume those files within the same attempt, so a review is never conducted against a
stale or absent image.

#### Scenario: Review reads the current attempt's render

- **WHEN** a part is re-rendered on a new attempt
- **THEN** the review for that attempt reads the files produced by that attempt, and
  no earlier or later render leaves the reviewed image missing or overwritten

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

