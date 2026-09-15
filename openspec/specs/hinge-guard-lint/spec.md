## Purpose

Quality-gate stage that makes a pre-existing, hand-rolled revolute-hinge script's
missing seating guard visible at gate time, not only a newly-authored one. Closes the
gap where a merged construction-time assertion (`cq_verify.verify_seated`) only helps a
part that is re-authored under the rule.

## Requirements

### Requirement: Hinge-associated script missing its seating guard is flagged
The quality gate SHALL provide a stage that, for a part script being
validated, determines whether any of its unions is "hinge-associated" —
either the `moving_union` of a `kinematics` entry with `type: "revolute"`, or
named in `members[].part` of a `joints` entry whose `block` is `pin_hinge` —
and, if so, inspects the script's AST for a call to
`cq_verify.verify_seated`, `cq_verify.verify_backed`, or
`blocks.joints.pin_hinge`. When a hinge-associated union's script contains a
boolean union call but none of those three, the stage SHALL emit one
`warning` finding (`source: "hinge_guard"`, `type: "hinge_guard_missing"`)
naming the union, `cq_verify.verify_seated`, and `blocks.joints.pin_hinge` as
the expected routes. The finding SHALL NOT block the gate.

#### Scenario: Hand-rolled hinge script with no guard call is flagged
- **WHEN** a plan's `kinematics` has an entry with `type: "revolute"` and
  `moving_union: "cradle"`, and `build/cradle.py`'s script builds a union via
  raw CadQuery calls with no `verify_seated`, `verify_backed`, or
  `pin_hinge` call anywhere in the script
- **THEN** the gate report's `issues` include one `hinge_guard_missing`
  warning naming the `cradle` union

#### Scenario: Script using verify_seated is silent
- **WHEN** the same plan's `build/cradle.py` calls
  `cq_verify.verify_seated(riser, knuckle, "-z", "hinge_ear")`
- **THEN** no `hinge_guard_missing` finding is emitted for that union

#### Scenario: Script built via the pin_hinge block is silent
- **WHEN** a part's script constructs its union via
  `blocks.joints.pin_hinge(...)`
- **THEN** no `hinge_guard_missing` finding is emitted for that union

#### Scenario: Non-hinge part is never checked
- **WHEN** a part's unions are not the `moving_union` of any revolute
  `kinematics` entry and not a member of any `pin_hinge` joint
- **THEN** the stage emits no finding for that script, regardless of what
  boolean calls it contains

#### Scenario: Multi-union script checks only its hinge-associated union
- **WHEN** a part declares two unions in its `unions` array, one of which is
  a revolute `kinematics` entry's `moving_union` and the other is not, and
  the script contains no guard call for either
- **THEN** the finding names only the hinge-associated union, not the
  unrelated one

#### Scenario: Ball-joint (spherical) kinematics is not covered by this check
- **WHEN** a `kinematics` entry has `type: "spherical"`
- **THEN** the stage does not treat that entry's `moving_union` as
  hinge-associated and emits no finding based on it
