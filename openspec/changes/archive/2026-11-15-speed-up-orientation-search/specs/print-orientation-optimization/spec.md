## ADDED Requirements

### Requirement: Candidate pruning preserves the exhaustive result

The optimizer SHALL be allowed to skip exact (bridge-aware) support evaluation of a
candidate only when cheap bounds prove it cannot be the selected candidate under the
active `optimize_for` mode, including that mode's tolerance bands, stability filter,
and tiebreak keys. The recommended rotation, the scores reported for it, and the
rationale SHALL equal those of scoring every candidate exactly. A candidate whose
bounds do not exclude it SHALL be evaluated exactly.

#### Scenario: Pruned search equals exhaustive search
- **WHEN** the optimizer runs with pruning on a mesh and again with every candidate
  evaluated exactly, in any `optimize_for` mode
- **THEN** both return the same `rotate`, `support_score`, `strength_score`,
  `bed_contact_mm2`, and `stable` values

#### Scenario: Bounds are conservative about bridges
- **WHEN** a candidate has a bridge region that discounts its cost by `BRIDGE_COST_FACTOR`
- **THEN** its lower bound is at most its exact cost, so it is never pruned while its
  exact cost could still win

#### Scenario: Tie on the primary key is not pruned
- **WHEN** a candidate's lower bound equals the incumbent's exact cost
- **THEN** it is evaluated exactly so the next tiebreak key (for example bed contact)
  decides

### Requirement: Search reports progress

While scoring candidates the optimizer SHALL report, to an optional caller-supplied
callback, the number of candidates handled out of the total, elapsed time, and an
estimated time remaining, no more often than a fixed minimum interval. With no callback
it SHALL emit nothing. The command-line tool SHALL write these lines to stderr so its
JSON stdout is unchanged.

#### Scenario: Progress lines during a long search
- **WHEN** a search over many candidates runs with a progress callback
- **THEN** the callback receives lines of the form "candidate i/N" with elapsed seconds
  and an ETA, spaced at least the minimum interval apart

#### Scenario: No callback
- **WHEN** the optimizer runs without a progress callback
- **THEN** nothing is printed and the result is unchanged

### Requirement: Scoring tessellation tolerance is explicit

`orientation_for` SHALL accept the linear and angular tolerance used to tessellate the
throwaway scoring mesh. The default SHALL remain the current tolerance until a coarser
default is validated against the existing fixtures to select the same orientations.

#### Scenario: Coarser tolerance yields a smaller mesh
- **WHEN** `orientation_for` is called with a coarser tolerance on a curved part
- **THEN** the scored mesh has fewer faces than at the default tolerance

#### Scenario: Default unchanged
- **WHEN** `orientation_for` is called without tolerance arguments
- **THEN** the tessellation is identical to before this change
