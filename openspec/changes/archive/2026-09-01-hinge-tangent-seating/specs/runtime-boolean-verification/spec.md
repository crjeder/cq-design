## ADDED Requirements

### Requirement: In-script helper detects a center-seated round join

The project SHALL provide a helper importable by a generated part script (via the
existing `PYTHONPATH=<src>` the wrapper sets), `verify_seated(support, boss, axis,
label, overlap=1.0)`, that checks whether a flat `support` body bites past the tangent
plane of a round `boss` body (a knuckle, boss, or other cylindrical/spherical feature)
along a signed axis token `"+x"`/`"-x"`/`"+y"`/`"-y"`/`"+z"`/`"-z"` identifying the
direction from `support` toward `boss`, using bounding-box comparison only. The bite
depth SHALL be computed as how far `support`'s bounding box extends past `boss`'s
bounding-box tangent face on the named axis. The check SHALL fail (raising
`RuntimeError`) when that bite depth exceeds the caller-supplied `overlap` tolerance
(default 1.0 mm, the minimal genuine-fusion margin) -- catching the case where a flat
riser or leg was positioned at the round feature's *center* coordinate instead of its
tangent, so the boss ends up more than half-buried in the support instead of standing
proud of it. On success the helper SHALL return `boss` unchanged so it chains inline
like the existing `verify_boolean`, `verify_feature_bounds`, `check_workplane`,
`verify_stage`, and `verify_backed` helpers. The raised error SHALL be marked
`[cq-verify:boss_swallowed:<label>] ...` and SHALL report the bite depth, the
`overlap` budget, and the caller-supplied `label`.

#### Scenario: Riser seated at the boss's center instead of its tangent

- **WHEN** a generated script builds a riser whose top face sits at a knuckle boss's
  center Z-coordinate rather than at `center_z - boss_radius`, and calls
  `verify_seated(riser, knuckle, "-z", label="hinge_ear")`
- **THEN** the helper raises `RuntimeError` marked `boss_swallowed` naming the `label`
  and reporting a bite depth equal to the boss's radius

#### Scenario: Riser correctly seated at the tangent

- **WHEN** a generated script builds a riser whose top face sits at the knuckle boss's
  tangent plane (within the `overlap` budget) and calls `verify_seated(riser, knuckle,
  "-z", label="hinge_ear")`
- **THEN** the helper returns the boss solid unchanged without raising

#### Scenario: Deliberate embedding stays under budget

- **WHEN** a generated script seats a boss with a small deliberate embed (e.g. 0.5 mm)
  for fusion margin, within the default 1.0 mm `overlap`
- **THEN** the helper returns the boss solid unchanged without raising

---

### Requirement: Wrapper maps center-seated join to a typed error

`run_cadquery_model.py` SHALL catch the `[cq-verify:boss_swallowed:<label>]` marked
`RuntimeError` and map it to a `boss_swallowed` entry in the JSON `errors` list,
alongside the existing `silent_boolean`, `feature_overflow`, `workplane_drift`,
`unbacked_mate`, and `stage_mismatch` typed errors, carrying the `label` and the bite
depth in the error message.

#### Scenario: Part script raises a boss-swallowed error

- **WHEN** a generated part script's subprocess run raises the
  `[cq-verify:boss_swallowed:<label>]` marked error
- **THEN** the wrapper's JSON output includes an `errors` entry with
  `"type": "boss_swallowed"` naming the `label`

---

### Requirement: Generated-script guidance directs hand-rolled knuckle joins to verify_seated

The part-generation guidance SHALL instruct that when a script hand-rolls a flat
support seating a round boss (a riser under a hinge knuckle, a rib against a boss,
or similar), the join SHALL be declared via `verify_seated` naming the round feature
as `boss` and the flat feature as `support`. This guidance applies only when the join
is hand-rolled from primitives; a join built by an existing block helper that already
seats at the tangent (e.g. `blocks.joints.pin_hinge`) does not need a separate
`verify_seated` declaration. This guidance SHALL live in both `prompts/part.md` and
the generated-script rules in `SKILL.md`.

#### Scenario: Hand-rolled hinge riser declares its seat

- **WHEN** a part script builds a riser under a round knuckle boss from primitives
  rather than via `blocks.joints.pin_hinge`
- **THEN** the guidance directs that join to be declared via `verify_seated` naming
  the knuckle as the boss

#### Scenario: Block-supplied hinge join is not required to re-declare

- **WHEN** a part script builds its hinge via `blocks.joints.pin_hinge`
- **THEN** the guidance does not require an additional `verify_seated` declaration for
  that hinge's knuckle-leaf join
