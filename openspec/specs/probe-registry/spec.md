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
`bbox` when the part declares dimensions; and, for each `interfaces[]` entry with
`position_mm` and `diameter_mm` or `size_mm`, probes chosen by a fixed interface-type
table in `probes.py` (cut-type interfaces get `empty_at`/`ray`, boss-type get
`solid_at`). The builder SHALL NOT add, edit or remove plan probes.

#### Scenario: Interface with position seeds a probe
- **WHEN** the plan declares a `screw_mount` interface at `[10, 10, 0]` with
  `diameter_mm: 3.2`
- **THEN** the registry holds a plan-owned probe asserting an open bore at that position

#### Scenario: Interface without position
- **WHEN** an interface has no `position_mm`
- **THEN** no probe is seeded for it and the report lists it under `unprobed_interfaces`

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

