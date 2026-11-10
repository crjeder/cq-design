## MODIFIED Requirements

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
