## MODIFIED Requirements

### Requirement: Connectedness is a mandatory invariant answered against sections

The single-connected-body invariant SHALL be evaluated for every part. When the
builder's contract carries a passing step report, the invariant SHALL be answered by the
report's `solids == 1` plan probe and the auditor prompt SHALL NOT ask it as a visual
question. Without a passing step report, it SHALL be answered against section views
that cross the part's body junctions -- not exterior or isometric panels alone, which
can overlap in projection and read as connected when they are not. The deterministic
`disconnected_body` wrapper error remains the blocking gate in both cases.

#### Scenario: Step report settles connectedness
- **WHEN** a part is audited with a passing step report
- **THEN** the audit prompt contains no connectedness question and the audit records
  connectedness as settled by the step report

#### Scenario: Disconnection visible only in section

- **WHEN** a part without a passing step report renders as separate solids that overlap
  in the exterior projection
- **THEN** the connectedness invariant is answered against a section crossing the
  junction, the answer is "no", and a `visual_mismatch` is recorded

#### Scenario: Connectedness invariant runs for every part

- **WHEN** any part is reviewed
- **THEN** the single-connected-body invariant is evaluated, by the step report or by
  sections, regardless of the part's declared features

## ADDED Requirements

### Requirement: Probe-settled feature questions are dropped from the audit
When the builder's contract carries a passing step report, `render_prompt.py audit`
SHALL omit questions about the presence, position and through-continuity of plan
interfaces that have a plan-owned probe in that report, and SHALL keep questions for
interfaces listed under `unprobed_interfaces`.

#### Scenario: Probed bore is not asked
- **WHEN** a screw-mount interface with `position_mm` has a passing plan probe
- **THEN** the audit prompt has no question about that bore's presence or depth

#### Scenario: Unprobed interface is still asked
- **WHEN** an interface has no `position_mm` and appears under `unprobed_interfaces`
- **THEN** the audit prompt keeps its feature question
