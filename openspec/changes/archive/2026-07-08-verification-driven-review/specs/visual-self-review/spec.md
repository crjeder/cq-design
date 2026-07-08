## REMOVED Requirements

### Requirement: Visual review uses a structured checklist injected as a reference
**Reason:** The open-ended checklist pass let the reviewer self-certify against one
image and miss defects a specific view would have shown (a part that should be one body
shipping as three detached solids). Replaced by a question-driven review whose questions
are generated from the plan and answered against cited views -- see "Visual review is
driven by generated verification questions".

## ADDED Requirements

### Requirement: Visual review is driven by generated verification questions

The skill SHALL drive the Phase 3 visual review as a set of concrete yes/no
verification questions rather than an open-ended inspection. Before the review, Claude
SHALL generate the question list for the part under review from its `BUILD_PLAN.json`
entry plus a fixed set of universal invariants:

- one question per `interfaces[]` entry (feature present, on the planned face, at the
  planned position),
- one question per `blocks_needed[]` entry (feature present),
- one question per declared union (the union is a single connected body), and
- the universal invariants, which always run: single connected body / no floating or
  detached solids; a flat face rests on the bed at Z=0; W:D:H proportions match the
  plan; the overall silhouette matches the description; the authored orientation is
  correct.

The skill SHALL provide the universal invariants and the per-feature question template
as an injected reference (the rewritten `reference/Visual Review Checklist.md`). Each
generated question SHALL be evaluated; the review passes only when every question is
answered affirmatively.

#### Scenario: Question list generated from the plan

- **WHEN** the part under review declares two interfaces, one block, and one union
- **THEN** the review evaluates a question for each interface, the block, and the
  union, plus the universal-invariant questions

#### Scenario: A single failed question is a mismatch

- **WHEN** one or more verification questions are answered "no"
- **THEN** the review result is a `visual_mismatch` naming the failed question(s), not
  a pass

## ADDED Requirements

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
