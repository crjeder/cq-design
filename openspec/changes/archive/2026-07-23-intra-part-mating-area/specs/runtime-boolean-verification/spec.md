## ADDED Requirements

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

## MODIFIED Requirements

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
