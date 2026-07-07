## ADDED Requirements

### Requirement: Up-facing gentle-incline area is reported as an advisory finding

The quality gate SHALL, for a part whose effective `optimize_for` is `visual_quality`,
measure the total surface area of **up-facing** gentle-incline faces at the part's chosen
print orientation and emit it as a single advisory finding. An up-facing gentle-incline
face is one whose outward normal at that orientation has `nz > 0` and whose inclination
from horizontal (`arccos(nz)`) is strictly greater than 5 degrees and strictly less than
45 degrees, excluding faces resting on the print bed. The finding SHALL use the shared
quality-gate issue contract `{source, severity, type, message, hint, ...}` with
`severity: "warning"`; it SHALL NOT be an error, because a shallow slope still prints.

#### Scenario: Shallow up-facing ramp is flagged under visual quality

- **WHEN** the gate runs on a `visual_quality` part that has a significant up-facing surface inclined ~20-30 degrees from horizontal at its chosen orientation
- **THEN** the gate emits one `warning` finding reporting the up-facing gentle-incline area, using the shared issue contract, and does not fail the gate on that finding alone

#### Scenario: Down-facing shallow faces are not counted

- **WHEN** a part's only sub-45-degree faces are down-facing (an overhang concern) and it has no up-facing gentle inclines
- **THEN** the cosmetic-slope finding is not emitted (the down-facing faces are left to the overhang check)

#### Scenario: Clean part produces no finding

- **WHEN** a `visual_quality` part's visible up-facing surfaces are all near-flat (<= 5 degrees) or steep (>= 45 degrees) at its chosen orientation
- **THEN** no cosmetic-slope finding is emitted

#### Scenario: Measured at the chosen orientation

- **WHEN** the part's chosen print orientation rotates an authored gentle up-facing slope to vertical (>= 45 degrees) in the build frame
- **THEN** that face is not counted as a cosmetic gentle incline (the measurement is taken in the print/build frame, not the authored frame)

---

### Requirement: The cosmetic-slope finding is gated on visual-quality intent

The gate SHALL emit the cosmetic-slope finding ONLY when the part's effective
`optimize_for` resolves to `visual_quality` (a per-part `optimize_for`, else the
plan-level `optimize_for`). For any other objective the check SHALL be a no-op that
emits nothing, so cosmetic slopes on functional parts do not nag.

#### Scenario: Structural part is not nagged

- **WHEN** the gate runs on a part whose effective `optimize_for` is `strength` (or `min_support`, or `min_build_height`)
- **THEN** no cosmetic-slope finding is emitted, regardless of the part's slope geometry

#### Scenario: Per-part visual override is honored

- **WHEN** the plan-level `optimize_for` is `strength` but the part declares its own `optimize_for: "visual_quality"`
- **THEN** the cosmetic-slope check runs for that part

---

### Requirement: The check degrades gracefully when inputs are missing

The check SHALL degrade to a `check_skipped` warning (never a crash and never an error)
when it cannot run: when the geometry backend (trimesh/numpy) is unavailable, or when the
part's chosen print orientation is not available so the measurement cannot be taken in the
build frame.

#### Scenario: Geometry backend unavailable

- **WHEN** trimesh/numpy cannot be imported
- **THEN** the check emits a single `check_skipped` warning and the gate continues

#### Scenario: Orientation unavailable

- **WHEN** a `visual_quality` part has no available chosen print orientation
- **THEN** the check emits a `check_skipped` warning rather than measuring in the authored frame
