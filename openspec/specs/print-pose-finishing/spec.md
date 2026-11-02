# Print Pose Finishing

## Purpose

Resolves orientation-dependent features (teardrop peak direction) from the accepted print pose: `print_up()` in part scripts, a pose-aware re-load at model export, a pose-stability guard, and pose provenance in the export manifest.
## Requirements
### Requirement: print_up reports print-up in the build pose
The `print_up()` helper SHALL return the print-up direction as a unit vector in the part's build pose, derived from `CQ_PRINT_ROTATE`, and SHALL return +Z when the variable is unset.

#### Scenario: Unset
- **WHEN** `CQ_PRINT_ROTATE` is not set
- **THEN** `print_up()` returns (0, 0, 1)

#### Scenario: Flipped pose
- **WHEN** `CQ_PRINT_ROTATE` is a 180 degree rotation about X
- **THEN** `print_up()` returns (0, 0, -1)

### Requirement: Teardrop blocks accept print_up
`teardrop_bore` and `teardrop_post` SHALL accept a `print_up` vector and orient their peak (bore) or flat (post) accordingly; `peak=` remains supported.

#### Scenario: Bore with flipped print-up
- **WHEN** `teardrop_bore(d, depth, print_up=(0, 0, -1))` is built
- **THEN** its apex lies at -Z

### Requirement: Finishing pass re-runs scripts with the accepted pose
After orientation is accepted and before model export, Phase 3 SHALL re-run each part script with `CQ_PRINT_ROTATE` set from `build/orientations.json`, without an LLM round.

#### Scenario: Pose available
- **WHEN** `build/orientations.json` has an entry for a part
- **THEN** the finishing run sets `CQ_PRINT_ROTATE` to that entry's `rotate` and the resulting geometry feeds export

#### Scenario: Authoring pass unchanged
- **WHEN** a script is run without `--print-rotate`
- **THEN** output is identical to the current behavior

### Requirement: Pose-stability guard
After the finishing pass the system SHALL re-score orientation and emit an advisory finding, keeping the accepted pose, if the newly chosen `rotate` differs.

#### Scenario: Pose shifts
- **WHEN** re-scoring picks a different `rotate` than the accepted one
- **THEN** an advisory finding names both poses and the accepted pose is kept

### Requirement: Finishing provenance
The export manifest SHALL record the `rotate` used in the finishing pass, and a mismatch with the current accepted orientation SHALL mark the export stale.

#### Scenario: Orientation re-accepted with a new pose
- **WHEN** `orientations.json` changes after export
- **THEN** freshness reports the export stale

### Requirement: Edge treatments are applied in the finishing pass by print-pose direction
For a step script, `Part.result()` SHALL return the body without edge treatments when
`CQ_PRINT_ROTATE` is unset. When it is set, `Part.result()` SHALL, for each plan instance
with an `edges` entry, map each named edge set to the final-body edges lying on that
set's placed curves, and treat each mapped edge with the declared size: chamfer when the
edge is horizontal in print pose, fillet when it is vertical or diagonal. Only this pass
SHALL apply cosmetic edge treatments; functional radii stay block geometry.

#### Scenario: Box edges in a rotated pose
- **WHEN** a `box` instance declares `edges: {"vertical": 1.0}` and the accepted pose
  lays the box on its side
- **THEN** the build-pose vertical edges, now horizontal, are chamfered 1.0 mm

#### Scenario: Step loop sees untreated geometry
- **WHEN** the step worker runs a script whose plan declares edge treatments
- **THEN** no edge is treated and orientation is later chosen on the untreated body

### Requirement: Probes are re-checked after edge treatment
After the finishing pass applies edge treatments, every plan-owned probe SHALL be
re-checked; block-owned probes inside a treated edge's zone SHALL retire. A failing
plan probe, or an edge set that maps to no final-body edge, SHALL raise a typed
`finishing_probe_failed` error with action `ask_user`.

#### Scenario: Chamfer breaks into a planned bore
- **WHEN** a 3 mm chamfer on a top edge removes material inside a plan-owned bore wall
  probe
- **THEN** the finishing pass reports `finishing_probe_failed` naming the edge set and
  the probe, and the step asks the user rather than routing to the builder

#### Scenario: Edge set lost after booleans
- **WHEN** a declared edge set maps to no edge of the final body
- **THEN** the finishing pass reports `finishing_probe_failed` naming the edge set

