# Runtime Boolean Verification

## Purpose

Defines requirements for `src/cq_verify.py`: construction-time assertions a generated
part script imports to catch three silent CadQuery failure modes at build time -- a
boolean that produced no change (tool did not overlap), a feature that extends past the
base body, and a workplane whose origin drifted -- so the offending feature can be named
in a typed error rather than surfacing downstream as a vague watertight/dimension symptom.

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
on a reused workplane, and SHALL NOT require wrapping every boolean, so trivially-
overlapping primitives stay uncluttered. This guidance SHALL live in both
`prompts/part.md` and the generated-script rules in `SKILL.md`.

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
