# Runtime Boolean Verification

## Purpose

Defines requirements for `src/cq_verify.py`: construction-time assertions a generated
part script imports to catch silent CadQuery failure modes at build time -- a
boolean that produced no change (tool did not overlap), a feature that extends past the
base body, a workplane whose origin drifted, and (for scratch-authored parts) a named
construction stage whose bbox/volume doesn't match the plan -- so the offending feature
or stage can be named in a typed error rather than surfacing downstream as a vague
watertight/dimension symptom.
## Requirements
### Requirement: In-script helper detects silent boolean failures

The project SHALL provide a helper importable by a generated part script (via the
existing `PYTHONPATH=<src>` the wrapper sets) that compares a solid before and after a
boolean operation and raises a `RuntimeError` when the operation produced no change.
The comparison SHALL consider a boolean a no-op only when the result's volume, face
count, AND bounding-box centroid are all unchanged within a small tolerance; if any one
differs, the boolean is treated as effective and no error is raised. The raised error
SHALL carry a caller-supplied `label` identifying the feature and the operation name.

#### Scenario: Cut tool misses the body

- **WHEN** a generated script calls the helper around a `.cut()` whose tool does not
  overlap the base body, leaving volume, face count, and centroid unchanged
- **THEN** the helper raises `RuntimeError` naming the operation and the supplied `label`

#### Scenario: Effective cut passes

- **WHEN** the helper wraps a `.cut()` that removes material (volume decreases and/or
  face count changes)
- **THEN** the helper returns the post-operation solid without raising

#### Scenario: Pure translation of equal-volume result is not flagged

- **WHEN** a boolean leaves volume and face count unchanged but shifts the centroid
  beyond the tolerance
- **THEN** the helper treats the operation as effective and does not raise

---

### Requirement: In-script helper detects feature-bounds overflow

The helper module SHALL provide a bounds check that compares a base body's bounding box
before and after adding a feature and raises `RuntimeError` when the post-feature
geometry extends past the base body's bounding box on any axis beyond a caller-supplied
tolerance. The error SHALL report the per-axis overflow magnitude and the feature
`label`.

#### Scenario: Added feature pokes past the body footprint

- **WHEN** an embossed feature unioned onto a body extends 2 mm past its X extent and
  the tolerance is 0.1 mm
- **THEN** the helper raises `RuntimeError` reporting the X overflow and the `label`

#### Scenario: Feature stays within the body

- **WHEN** an added feature's bounding box stays within the base body's bounding box
  plus tolerance on every axis
- **THEN** the helper returns the post-feature solid without raising

---

### Requirement: In-script helper detects workplane-origin drift

The helper module SHALL provide a workplane check that raises `RuntimeError` when a
workplane's origin has drifted from a caller-supplied expected point by more than a
caller-supplied tolerance. This catches the CadQuery trap where `.center()` (and other
origin-shifting operations) permanently move the workplane origin, so a subsequently
placed feature lands at the wrong location without any exception. The error SHALL report
the expected origin, the actual origin, the drift distance, and the caller-supplied
`label`. When the origin is within tolerance the check SHALL return the workplane
unchanged so it can be used inline.

#### Scenario: Workplane origin drifted after `.center()`

- **WHEN** a script asserts an expected origin on a workplane whose origin was shifted by
  a prior `.center()` beyond the tolerance
- **THEN** the helper raises `RuntimeError` reporting expected vs. actual origin, the
  drift distance, and the `label`

#### Scenario: Workplane origin still at the expected point

- **WHEN** the workplane's origin matches the expected point within tolerance
- **THEN** the helper returns the workplane without raising

---

### Requirement: In-script helper detects an unbacked mating area

The project SHALL provide a helper importable by a generated part script (via the
existing `PYTHONPATH=<src>` the wrapper sets) that checks whether one face of a
`feature` solid -- named by a signed axis token `"+x"`/`"-x"`/`"+y"`/`"-y"`/`"+z"`/`"-z"`
identifying the direction from the feature's interior toward its intended neighbor -- is
fully backed by a `backer` solid, using bounding-box comparison only. The check SHALL
fail (raising `RuntimeError`) when either:

- the `backer`'s bounding box does not reach the feature's contact-face coordinate on the
  named axis beyond a caller-supplied tolerance, or
- on either of the two axes orthogonal to the named axis, the `feature`'s bounding-box
  range is not fully contained within the `backer`'s bounding-box range at that contact
  plane, beyond the tolerance.

On success the helper SHALL return `feature` unchanged so it chains inline like the
existing `verify_boolean`, `verify_feature_bounds`, `check_workplane`, and `verify_stage`
helpers. The raised error SHALL be marked `[cq-verify:unbacked_mate:<label>] ...` and
SHALL report which check failed (reach vs. containment), the orthogonal axis involved
when it is a containment failure, and the caller-supplied `label`.

#### Scenario: Feature only partially backed by its neighbor

- **WHEN** a generated script declares a standoff's `-z` face must be backed by a leg,
  and the standoff's bounding-box range on the Y axis extends beyond the leg's Y range
  by more than the tolerance
- **THEN** the helper raises `RuntimeError` marked `unbacked_mate` naming the `label` and
  the Y-axis containment failure

#### Scenario: Backer does not reach the contact plane

- **WHEN** a generated script declares a feature's `-z` face must be backed by a solid
  whose bounding box stops short of that Z coordinate by more than the tolerance
- **THEN** the helper raises `RuntimeError` marked `unbacked_mate` naming the `label` and
  the reach failure

#### Scenario: Feature fully backed

- **WHEN** a generated script declares a feature's face must be backed by a solid whose
  bounding box reaches the contact plane and fully contains the feature's range on both
  orthogonal axes, within tolerance
- **THEN** the helper returns the feature solid unchanged without raising

---

### Requirement: Wrapper maps unbacked-mate to a typed error

`run_cadquery_model.py` SHALL catch the `[cq-verify:unbacked_mate:<label>]` marked
`RuntimeError` and map it to an `unbacked_mate` entry in the JSON `errors` list,
alongside the existing `silent_boolean`, `feature_overflow`, `workplane_drift`, and
`stage_mismatch` typed errors, carrying the `label` and the failing-check detail
(reach vs. containment, and the orthogonal axis when applicable) in the error message.

#### Scenario: Part script raises an unbacked-mate error

- **WHEN** a generated part script's subprocess run raises the
  `[cq-verify:unbacked_mate:<label>]` marked error
- **THEN** the wrapper's JSON output includes an `errors` entry with
  `"type": "unbacked_mate"` naming the `label`

---

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

---

### Requirement: Helper adds no new third-party dependency

The helper module SHALL depend only on CadQuery (already a required dependency) and the
Python standard library, so that a generated script importing it runs in the same
environment as any other part script with no additional install step.

#### Scenario: Import in a generated script

- **WHEN** a generated part script imports the helper under the wrapper's `PYTHONPATH`
- **THEN** the import succeeds without requiring any package beyond the project's
  existing dependencies

---

### Requirement: Generated-script guidance prescribes when to verify

The part-generation guidance SHALL instruct that a boolean be wrapped in a verify call
when a silent no-op is plausible -- specifically a tool positioned by a computed offset,
a feature not at the bounding-box center, or an embossed/debossed text merge -- that a
workplane origin be asserted after a `.center()`/`.hole()` before a new feature is placed
on a reused workplane, and that a feature's mating area be declared with `verify_backed`
when that feature (a standoff, boss, rib, ear, or gusset) must be fully supported by a
specific named neighboring feature at one particular face -- as distinct from a feature
that legitimately extends past its base on other axes, which is not a mating-area case.
The guidance SHALL NOT require wrapping every boolean or declaring a mating area for
every adjacency, so trivially-overlapping primitives and ordinary base-body containment
stay uncluttered. This guidance SHALL live in both `prompts/part.md` and the
generated-script rules in `SKILL.md`.

#### Scenario: Off-center cut is wrapped

- **WHEN** a part script cuts a slot positioned by a computed offset into a body that
  has other features
- **THEN** the guidance directs that cut to be wrapped in the boolean-verify helper

#### Scenario: Reused workplane after `.center()` is asserted

- **WHEN** a part script places a new feature on a workplane it previously shifted with
  `.center()`
- **THEN** the guidance directs a workplane-origin assertion before placing that feature

#### Scenario: Trivial primitive union is left unwrapped

- **WHEN** a part script unions a boss centered on and clearly overlapping the base body
- **THEN** the guidance does not require wrapping that union

#### Scenario: Standoff feature declares its mating area

- **WHEN** a part script builds a standoff post that must be fully supported by a
  specific leg feature at the standoff's base face
- **THEN** the guidance directs that face to be declared via `verify_backed` naming the
  leg as the backer

#### Scenario: Intentional cross-axis overflow is not treated as a mating-area case

- **WHEN** a part script builds a feature that legitimately extends past its base body
  on an axis unrelated to any declared contact face (e.g. a post rising in Z off a base)
- **THEN** the guidance does not require a `verify_backed` declaration for that overflow

---

### Requirement: In-script helper detects construction-stage mismatch

The project SHALL provide a helper importable by a generated part script (via the
existing `PYTHONPATH=<src>` the wrapper sets) that checks a Workplane/solid at a
named construction stage against a caller-supplied expected bounding box and/or
minimum volume. At least one of `bbox` or `vol_min` SHALL be supplied. The helper
SHALL raise a `RuntimeError` marked `[cq-verify:stage_mismatch:<label>] ...` when the
supplied bbox does not match within tolerance, or the volume is below `vol_min`. On
success the helper SHALL return the input unchanged so it chains inline like the
existing `verify_boolean`, `verify_feature_bounds`, and `check_workplane` helpers.

#### Scenario: Stage bbox mismatch

- **WHEN** a generated script asserts an expected bounding box for a named stage and
  the actual bbox differs beyond tolerance
- **THEN** the helper raises `RuntimeError` naming the stage `label` and reporting
  expected vs. actual bbox

#### Scenario: Stage volume below minimum

- **WHEN** a generated script asserts a `vol_min` for a named stage and the actual
  solid's volume is below it
- **THEN** the helper raises `RuntimeError` naming the stage `label` and reporting
  the actual volume vs. `vol_min`

#### Scenario: Stage matches expectations

- **WHEN** a stage's bbox and/or volume are within the asserted expectations
- **THEN** the helper returns the input Workplane/solid unchanged without raising

---

### Requirement: Wrapper maps stage mismatch to a typed error

`run_cadquery_model.py` SHALL catch the `[cq-verify:stage_mismatch:<label>]` marked
`RuntimeError` and map it to a `stage_mismatch` entry in the JSON `errors` list,
alongside the existing `silent_boolean`, `feature_overflow`, and `workplane_drift`
typed errors, carrying the stage `label` and mismatch detail in the error message.

#### Scenario: Scratch part script raises a stage mismatch

- **WHEN** a generated part script's subprocess run raises the
  `[cq-verify:stage_mismatch:<label>]` marked error
- **THEN** the wrapper's JSON output includes an `errors` entry with
  `"type": "stage_mismatch"` naming the stage `label`

---

### Requirement: In-script helper checks a fillet radius before the kernel

`cq_verify` SHALL provide `check_fillet(body, radius, selector=None, label="")` that
measures the edges of `body` selected by `selector` (all edges when `None`) and raises
a marked `RuntimeError` `[cq-verify:fillet_radius:<label>]` when `radius` is greater
than or equal to the limit set by any adjacent edge. An adjacent edge is any other edge of
`body` that shares a vertex with a selected edge; its limit is its length, halved when
both of its ends touch a selected edge other than itself. The error
detail SHALL report the requested radius, the computed limit, and the selector. On
success the helper SHALL return `body` unchanged without calling the kernel's fillet.

#### Scenario: Radius exceeds the adjacent edge

- **WHEN** a script calls `check_fillet(box(20, 20, 5), 6, ">Z", "lid_edge")`
- **THEN** the helper raises `RuntimeError` marked `fillet_radius` naming `lid_edge`
  and reporting a 5.00 mm limit

#### Scenario: Valid radius passes through

- **WHEN** a script calls `check_fillet(box(20, 20, 5), 2, ">Z", "lid_edge")`
- **THEN** the helper returns the same `body` object

#### Scenario: Edges shared from both ends halve the limit

- **WHEN** a script calls `check_fillet(box(20, 20, 5), 3, "|Z", "corners")`
- **THEN** the helper does not raise, because the 20 mm horizontals give a 10 mm limit
  and the parallel 5 mm verticals are not adjacent edges

---

### Requirement: In-script helper checks a chamfer length before the kernel

`cq_verify` SHALL provide `check_chamfer(body, length, selector=None, label="")`
applying the same adjacent-edge rule as `check_fillet` to a symmetric chamfer length,
raising `[cq-verify:chamfer_size:<label>]` on violation and returning `body` unchanged
on success.

#### Scenario: Chamfer too large

- **WHEN** a script calls `check_chamfer(box(20, 20, 5), 5, ">Z", "top_chamfer")`
- **THEN** the helper raises `RuntimeError` marked `chamfer_size` naming `top_chamfer`

#### Scenario: Chamfer within limit

- **WHEN** a script calls `check_chamfer(box(20, 20, 5), 1, ">Z", "top_chamfer")`
- **THEN** the helper returns the same `body` object

---

### Requirement: In-script helper checks a hole ligament

`cq_verify` SHALL provide `check_ligament(wall_mm, hole_d_mm, min_mm, label="")` that
computes the ligament on each side of a hole centered in a wall as
`(wall_mm - hole_d_mm) / 2` and raises `[cq-verify:thin_ligament:<label>]` when it is
below `min_mm`, reporting the ligament and `min_mm`. On success it SHALL return the
ligament in mm.

#### Scenario: Ligament below minimum

- **WHEN** a script calls `check_ligament(6, 5, 1.2, "m5_boss")`
- **THEN** the helper raises `RuntimeError` marked `thin_ligament` naming `m5_boss`
  and reporting a 0.50 mm ligament

#### Scenario: Ligament sufficient

- **WHEN** a script calls `check_ligament(10, 5, 1.2, "m5_boss")`
- **THEN** the helper returns 2.5

---

### Requirement: Wrapper maps pre-kernel predicate failures to typed errors

`run_cadquery_model.py` SHALL register `fillet_radius`, `chamfer_size`, and
`thin_ligament` in `_VERIFY_HINTS`, so a marked failure becomes an `errors` entry with
that `type`, the `label`, the detail as `message`, and a non-empty `hint`, instead of
an `occ_exception`.

#### Scenario: Over-large fillet in a script

- **WHEN** a part script calls `check_fillet` with a radius above the limit before its
  `.fillet()` call and is run through `run_cadquery_model.py`
- **THEN** the JSON has `success: false` and `errors[0].type == "fillet_radius"` with a
  non-empty `hint`, and no `occ_exception` entry

#### Scenario: Marker strings classify

- **WHEN** stderr ends with `RuntimeError: [cq-verify:<kind>:x] detail` for each of
  the three kinds
- **THEN** `_translate_stderr` returns one entry whose `type` is that kind

---

### Requirement: Generated-script guidance covers the pre-kernel predicates

The "Construction-time verification" section of `prompts/part.md` SHALL show
`check_fillet`, `check_chamfer`, and `check_ligament` in its import example, state the
adjacent-edge rule in one line, and direct the author to call `check_fillet` /
`check_chamfer` before a fillet or chamfer whose size is computed from parameters or
approaches a wall or edge dimension, and `check_ligament` before a hole placed in a
wall sized from a parameter.

#### Scenario: Prompt documents the helpers

- **WHEN** the rendered part prompt is read
- **THEN** its Construction-time verification section names all three helpers, their
  typed error kinds, and the adjacent-edge rule

