## MODIFIED Requirements

### Requirement: The plan's review policy selects progressive or autonomous build per part

The Phase 3 part loop SHALL decide per part whether to build progressively (staged,
with user checkpoints) or autonomously (the existing single-shot loop), driven by
the plan's effective `review_policy` (see `planning-phase` spec):

- `every_stage` (default): every part builds progressively.
- `checkpoints`: a part builds progressively when it has at least one `interfaces`
  entry OR its `blocks_needed` count meets or exceeds a stated threshold (the
  complexity gate); otherwise it builds autonomously. The gate condition and
  threshold SHALL be stated as tunable values in the Phase 3 build documentation
  (`skill/phase3_build.md`).
- `minimal`: every part builds autonomously; no stage checkpoints are shown.

#### Scenario: every_stage builds every part progressively

- **WHEN** the plan's effective `review_policy` is `every_stage`
- **THEN** every part is built progressively with user checkpoints between stages,
  regardless of its interfaces or blocks_needed count

#### Scenario: checkpoints applies the complexity gate

- **WHEN** the plan's effective `review_policy` is `checkpoints` and a part has at
  least one `interfaces` entry or a `blocks_needed` count at or above the threshold
- **THEN** the part is built progressively with user checkpoints between stages

#### Scenario: checkpoints skips simple parts

- **WHEN** the plan's effective `review_policy` is `checkpoints` and a part has no
  `interfaces` and a `blocks_needed` count below the threshold
- **THEN** the part is built with the existing autonomous part loop and no
  progressive checkpoints are shown

#### Scenario: minimal builds every part autonomously

- **WHEN** the plan's effective `review_policy` is `minimal`
- **THEN** every part is built with the existing autonomous part loop and no
  progressive checkpoints are shown

#### Scenario: Gate values are stated in the Phase 3 build documentation

- **WHEN** a reader consults `skill/phase3_build.md`
- **THEN** the complexity gate condition and threshold used under `checkpoints` are
  stated explicitly as tunable values

### Requirement: Build mode is user-overridable regardless of the review policy

The user SHALL be able to force progressive build or force autonomous build for a
part or a run, overriding the effective `review_policy`-driven selection. Absent an
override, the `review_policy` selection SHALL apply.

#### Scenario: User forces autonomous on a part that review_policy would stage

- **WHEN** the user opts out of progressive build for a part that the effective
  `review_policy` would otherwise build progressively
- **THEN** the part is built autonomously with no checkpoints

#### Scenario: User forces progressive on a part that review_policy would not stage

- **WHEN** the user opts in to progressive build for a part that the effective
  `review_policy` would otherwise build autonomously
- **THEN** the part is built progressively with checkpoints

#### Scenario: No override uses the review policy

- **WHEN** the user gives no mode override
- **THEN** the plan's effective `review_policy` decides the mode, per the previous
  requirement
