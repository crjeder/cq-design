## ADDED Requirements

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
