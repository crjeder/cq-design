# toolpath-speed-advisor Specification

## Purpose

Estimate a part's print time from its toolpath geometry and the printer's motion
constraints, attribute time loss to sharp corners versus feature crowding, and detect when
a pose is bound by minimum layer time -- as an advisory finding, never a gate.

## Requirements

### Requirement: Corner speed is a single continuous formula

The system SHALL compute a sustainable corner speed for every edge of a part's authored
result as `v_corner = min(v_cruise, sqrt(a * R_eff))`, where `a` is `motion.accel_mm_s2`
and `v_cruise` is `motion.v_cruise_mm_s`, both read from `printer_profile.json`. `R_eff`
SHALL be the edge's fillet radius when the edge is a filleted (arc/cylindrical) edge, and
SHALL otherwise be derived from the edge's exterior turn angle `phi` (the angle between
the tangent directions of the two adjacent faces) as
`R_eff = JD * cos(phi/2) / (1 - cos(phi/2))`, where `JD` is
`motion.junction_deviation_mm`. A straight edge (`phi` at or near 0) SHALL yield an
unbounded `R_eff` (no corner limit). The two cases SHALL agree at the boundary: a fillet
of radius `R` and a sharp corner of the equivalent turn angle SHALL NOT be scored by
different formulas.

#### Scenario: Sharp corner yields a finite effective radius
- **WHEN** an untreated edge has an exterior turn angle of 90 degrees
- **THEN** its `R_eff` is computed from the junction-deviation formula and is a small,
  finite, positive value, not zero and not infinite

#### Scenario: Straight edge has no corner limit
- **WHEN** an edge's exterior turn angle is at or near 0 degrees
- **THEN** its `R_eff` is unbounded and `v_corner` equals `v_cruise`

#### Scenario: Filleted edge uses its own radius
- **WHEN** an edge is a filleted (arc) edge with radius `R`
- **THEN** `R_eff` equals `R` and `v_corner = min(v_cruise, sqrt(a * R))`

#### Scenario: Larger radius never sustains a lower speed
- **WHEN** two edges are compared at the same turn angle, one sharp and one filleted with
  a growing radius
- **THEN** `v_corner` is monotonically non-decreasing as the fillet radius increases, up to
  the `v_cruise` ceiling

### Requirement: Print time decomposes into ideal, corner, and crowding terms

The system SHALL compute, for a part's build-pose edge/face graph oriented to a given
build pose, three time quantities that satisfy
`T_actual = T_ideal + T_corners + T_crowding` exactly:
- `T_ideal`: total path length divided by `v_cruise`.
- `T_corners`: the sum, over every corner, of the isolated single-corner deceleration/
  reacceleration cost `(v_cruise - v_corner)^2 / (a * v_cruise)`, as if each corner sat on
  an infinitely long segment.
- `T_crowding`: the remainder, computed as `T_actual - T_ideal - T_corners`, where
  `T_actual` is the trapezoid-profile traversal time of the closed path honoring each
  segment's own length (a segment shorter than the accel/decel distance never reaches
  `v_cruise`).

`T_crowding` SHALL be non-negative for any valid path. The system SHALL report
`speed_efficiency = T_ideal / T_actual`.

#### Scenario: Terms sum to actual time
- **WHEN** the three time quantities are computed for any part's build-pose path
- **THEN** `T_ideal + T_corners + T_crowding` equals `T_actual` to within floating-point
  tolerance

#### Scenario: Crowding is never negative
- **WHEN** every segment of a path is shorter than the distance needed to reach cruise
  speed
- **THEN** `T_crowding` is greater than or equal to zero

#### Scenario: Sparse, well-filleted part has high efficiency
- **WHEN** a part's segments are long relative to the accel/decel distance and its corners
  are gently filleted
- **THEN** `speed_efficiency` is close to 1.0

### Requirement: Findings attribute time loss to corners or to feature crowding

When `T_corners` is the larger of the two loss terms, the system SHALL report a ranked,
per-edge attribution table. Each edge's attributed value SHALL be computed leave-one-out:
`T_actual` recomputed with that edge's `R_eff` set to unbounded, minus the real
`T_actual`. When the leave-one-out values do not sum to `T_corners` (corners interacting
because they are close together), the system SHALL state this explicitly rather than
silently presenting a table that appears to be exhaustive.

When `T_crowding` is the larger of the two loss terms, the system SHALL report a single
finding stating that the part's typical feature size is too small for the toolhead to
reach cruise speed, and SHALL suggest fewer, larger features as the remedy, without
attempting to rank individual features.

The system SHALL NOT emit either finding when `speed_efficiency` is at or above a stated
reporting threshold; a part already printing efficiently gets no attribution table.

#### Scenario: Corner-dominant part gets a ranked table
- **WHEN** `T_corners` exceeds `T_crowding` and `speed_efficiency` is below the reporting
  threshold
- **THEN** the result lists edges ranked by leave-one-out time recovered, most first

#### Scenario: Crowding-dominant part gets a feature-size finding
- **WHEN** `T_crowding` exceeds `T_corners` and `speed_efficiency` is below the reporting
  threshold
- **THEN** the result states that feature size limits speed and recommends fewer, larger
  features, without a per-edge table

#### Scenario: Efficient part produces no findings
- **WHEN** `speed_efficiency` is at or above the reporting threshold
- **THEN** no corner table and no crowding finding are emitted

### Requirement: Corner findings survive a minimum-layer-time stall

When the part's estimated pose is minimum-layer-time bound (see the layer-time
requirement below), the system SHALL still emit corner and crowding findings when
`speed_efficiency` is below the reporting threshold, but SHALL state that no print-time
benefit is available in the stalled state and SHALL rephrase the finding's rationale
around reduced vibration, ringing, and mechanical wear rather than time saved. The system
SHALL NOT suppress or withhold corner findings solely because the pose is stalled.

#### Scenario: Stalled part still reports sharp-edge findings
- **WHEN** a pose is minimum-layer-time bound and the part has low `speed_efficiency`
- **THEN** the corner/crowding findings are still emitted, with a rationale referring to
  vibration and wear rather than time recovered

#### Scenario: Stalled part's time recovery is reported as zero
- **WHEN** a pose is minimum-layer-time bound
- **THEN** any reported time-recovery figure for a fillet suggestion is zero, and the stall
  is named as the reason

### Requirement: Mean layer perimeter and infill path are derived from posed mesh areas

The system SHALL compute a mean layer perimeter as `A_lateral / H`, where `A_lateral` is
the posed mesh's total surface area minus its up-facing and down-facing area (using the
same normal-partitioned area sums used for the support score) and `H` is the posed
bounding-box height. The system SHALL compute an estimated per-layer infill path length
from the part's cross-sectional area (`volume / H`) minus the area covered by the
perimeter bands (`perimeter_count * line_width * P_mean`), scaled by `motion.infill_density`
and divided by `motion.line_width_mm`, floored at zero.

#### Scenario: Thin-walled part attributes all path to perimeters
- **WHEN** a part's wall thickness times perimeter count accounts for nearly its entire
  cross-sectional area
- **THEN** the estimated infill path length is at or near zero

#### Scenario: Solid part adds an infill path term
- **WHEN** a part's cross-sectional area substantially exceeds its perimeter-band area
- **THEN** the estimated infill path length is positive and scales with the uncovered area

### Requirement: Minimum layer time is detected and drives total time when binding

The system SHALL compute an estimated per-layer time `t_layer = L_layer /
(speed_efficiency * v_cruise)`, where `L_layer` is the sum of the perimeter and infill
path lengths. When `t_layer` is less than `motion.min_layer_time_s`, the system SHALL
report the pose as stalled and SHALL compute total estimated print time as
`(H / motion.layer_height_mm) * motion.min_layer_time_s`, independent of any further
geometry change other than height. When not stalled, total estimated print time SHALL be
`(H / motion.layer_height_mm) * t_layer`.

#### Scenario: Short layer path triggers a stall
- **WHEN** `t_layer` is less than `motion.min_layer_time_s`
- **THEN** the result reports the pose as stalled and total time is driven by height and
  the minimum layer time alone

#### Scenario: Longer layer path is not stalled
- **WHEN** `t_layer` is at or above `motion.min_layer_time_s`
- **THEN** the result reports the pose as not stalled and total time uses the computed
  `t_layer`

### Requirement: Stall remedies name copies-per-plate but never apply it

When a pose is reported as stalled, the system SHALL state, as candidate remedies: a
flatter pose (build-height reduction), thickening the stalling feature, and increasing
the number of copies on the same plate. The system SHALL NOT modify plate layout, part
count, or `BUILD_PLAN.json` to apply the copies remedy; that change SHALL occur only after
explicit user approval, recorded the same way any other plan correction is recorded.

#### Scenario: Stall report lists copies as an option
- **WHEN** a pose is reported as stalled
- **THEN** the reported remedies include increasing copies per plate, alongside re-posing
  and thickening

#### Scenario: The advisor never changes plate layout itself
- **WHEN** the advisor runs and detects a stall
- **THEN** `BUILD_PLAN.json`, plate assignment, and part count are unchanged by the
  advisor's own action

### Requirement: The advisor runs in build pose during build and print pose at the gate

During Phase 3 part authoring, the system SHALL report corner and crowding findings using
the part's build-pose geometry, stating that the findings are conditional on the
part's eventual build orientation. At the quality-gate stage, the system SHALL recompute
the same findings using the union's accepted print orientation, re-extracting the corner
model from the union's geometry rigidly transformed into that orientation, producing the
pose-real numbers reported in the delivered print recipe.

#### Scenario: Build-pose hint during part authoring
- **WHEN** the advisor runs during Phase 3 before an orientation has been chosen
- **THEN** its findings are computed in the part's build pose and state that they are
  conditional on final build orientation

#### Scenario: Print-pose numbers at delivery
- **WHEN** the advisor runs at the quality gate with an accepted orientation available
- **THEN** its findings are computed by re-extracting the corner model from the union's
  geometry transformed into that orientation, and the reported numbers reflect the
  actual print pose

### Requirement: The advisor is advisory and degrades to a stated skip

`src/toolpath_speed.py` SHALL always exit 0 and SHALL NOT add a `quality_gate.py` stage
capable of failing the gate. Findings SHALL be emitted at `severity: "warning"` in the
shared quality-gate issue contract. When `printer_profile.json` has no `motion` block, or
when the part's geometry cannot be represented by the mean-layer-perimeter model (e.g. the
model's height-coverage fraction falls below a stated floor), the system SHALL emit
`{"status": "skipped", "reason": ...}` and SHALL NOT report any finding.

#### Scenario: Missing motion block skips cleanly
- **WHEN** `printer_profile.json` has no `motion` block
- **THEN** the advisor reports a skipped status naming the missing block and exits 0

#### Scenario: Non-prismatic geometry skips cleanly
- **WHEN** the part's height-coverage fraction under the mean-layer-perimeter model falls
  below the stated floor
- **THEN** the advisor reports a skipped status naming the reason and exits 0

#### Scenario: A finding never fails the gate
- **WHEN** the advisor reports a corner or crowding finding
- **THEN** the quality gate's overall pass/fail is unaffected by that finding
