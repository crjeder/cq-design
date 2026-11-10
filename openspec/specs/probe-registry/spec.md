# probe-registry Specification

## Purpose
TBD - created by archiving change step-loop-probes. Update Purpose after archive.
## Requirements
### Requirement: Probe kinds
`src/probes.py` SHALL provide the probe kinds `solid_at(point)`, `empty_at(point)`,
`ray(point, dir, hits)`, `bbox(lo, hi, tol)` and `delta(sign)`, each evaluated in-process
on the BRep body (point classification and line intersection), without meshing.

#### Scenario: Through-hole checked by ray
- **WHEN** a `ray` probe along the bore axis expects 2 hits (enter and exit of the
  surrounding material, none inside the bore)
- **THEN** the probe passes only if the bore is open over the full length

### Requirement: Every inventory entry declares local-frame probes
Every block, template and primitive SHALL declare a probe function returning its probes
in its local frame for given parameters. A template's probes SHALL cover every feature
it builds. Probe points SHALL lie at least `max(0.1 mm, 10 * tolerance)` from the
entry's own faces.

#### Scenario: Default build passes its own probes
- **WHEN** the test suite builds each inventory entry with its default parameters
- **THEN** every probe the entry declares passes on that build

#### Scenario: Entry without probes
- **WHEN** an inventory entry has no probe function
- **THEN** the inventory test fails naming the entry

### Requirement: Place transforms probes into the registry
A `place` step SHALL transform the entry's probes with the same location and rotation
as its solid, add a `delta` probe matching `op` (`union` positive, `cut` negative), and
append them to the part's probe registry owned by that step.

#### Scenario: Boss probes follow placement
- **WHEN** a screw boss is placed at (10, 10, 4)
- **THEN** its bore `empty_at` probe in the registry lies at (10, 10, 4 + its local z)

### Requirement: Plan-derived probes at step 0
Before the first step, the registry SHALL be seeded from the part's plan entry: a
`solids == 1` invariant checked after every step from the first `place`; an envelope
`bbox` when the part declares dimensions; for each `interfaces[]` entry with
`position_mm` and `diameter_mm` or `size_mm`, probes chosen by a fixed interface-type
table in `probes.py` (cut-type interfaces get `empty_at`/`ray`, boss-type get
`solid_at`); and every entry of the part's authored `probes[]`, converted unchanged to a
probe of its `kind` with its `label` and optional `instance`. Authored probes SHALL be
plan-owned: armed when their `instance` is placed, or only at the final check when they
name no instance, never retired, and part of the step cache key. The builder SHALL NOT
add, edit or remove plan probes.

#### Scenario: Interface with position seeds a probe
- **WHEN** the plan declares a `screw_mount` interface at `[10, 10, 0]` with
  `diameter_mm: 3.2`
- **THEN** the registry holds a plan-owned probe asserting an open bore at that position

#### Scenario: Interface without position
- **WHEN** an interface has no `position_mm`
- **THEN** no probe is seeded for it and the report lists it under `unprobed_interfaces`

#### Scenario: Authored probe seeds the registry
- **WHEN** a part declares `probes: [{"kind": "empty_at", "p": [6, 6, 2], "label": "M3 hole 6 mm from both edges"}]`
- **THEN** the registry holds a plan-owned `empty_at` probe at `[6, 6, 2]` with that label

#### Scenario: Authored probe fails on a body missing its feature
- **WHEN** an authored `empty_at` probe names no instance and the finished body is solid at its point
- **THEN** the final check fails on that probe and reports its label and observed state

#### Scenario: Authored probe waits for its instance
- **WHEN** an authored probe names `instance: "mount_hole"` and that instance is not yet placed
- **THEN** the probe is not checked by earlier steps and is checked from the `mount_hole` place step on

#### Scenario: Changing an authored probe invalidates the step cache
- **WHEN** an authored probe's point changes between two runs of the same step script
- **THEN** the part's step key changes, so no cached step state is reused

### Requirement: Probes accumulate and are re-checked after every step
Every probe in the registry SHALL be re-checked after every later step. A block-owned
probe whose point lies inside a later step's tool envelope SHALL be retired by that step
and listed under `retired`, not failed. Plan-owned probes SHALL never be retired.

#### Scenario: Counterbore retires a boss wall probe
- **WHEN** a counterbore cut overlaps a boss's `solid_at` wall probe
- **THEN** that probe is reported `retired` by the counterbore step and the step passes

#### Scenario: Plan probe cannot be retired
- **WHEN** a union step's envelope contains a plan-owned `empty_at` probe and fills it
- **THEN** the step fails on that probe

