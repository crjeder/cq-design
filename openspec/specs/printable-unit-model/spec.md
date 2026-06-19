# printable-unit-model Specification

## Purpose

Define how a build plan models a fabricated product as a set of rigid *unions*
grouped into *plates*, each union carrying its pose in a shared assembled frame.
This is the structural source of truth consumed by the model-level export and the
whole-model kinematic check.

## Requirements

### Requirement: Each union declares its assembled placement

Each union SHALL carry an optional `placement` describing its pose in the shared
assembled frame: a `translate_mm` (`[x, y, z]`) and an ordered `rotate` list of
`{axis, angle_deg}` steps (`axis` one of `X`, `Y`, `Z`). Rotations SHALL apply in
listed order, then the translation. An absent `placement` SHALL mean identity (the
union is authored directly in the assembled frame). The placement SHALL be the
single structured source of truth for assembled position, consumed by both the
model-level export and the kinematic check.

#### Scenario: Union without placement is in the assembled frame as authored
- **WHEN** a union omits `placement`
- **THEN** its as-authored geometry is treated as already in the assembled frame

#### Scenario: Placement positions a union in the assembled frame
- **WHEN** a lid union declares `placement` with a rotation and translation
- **THEN** the model export and the kinematic check both position the lid by
  applying its rotations in order followed by its translation

---

### Requirement: The build plan distinguishes unions from plates

The build plan SHALL model a *union* as one rigid body (one connected solid, the
unit of motion and the subject of kinematic checks) and a *plate* as a set of
unions fabricated in one print job. Each union SHALL declare the `plate` it belongs
to. The default SHALL be one union per plate. A print-in-place mechanism SHALL be
expressed as several unions sharing one `plate`. Plate membership SHALL NOT affect
the kinematic check, which operates on per-union meshes regardless of plate.

#### Scenario: Ordinary part is one union on its own plate
- **WHEN** a part has no internal degree of freedom
- **THEN** it is a single union assigned to its own plate

#### Scenario: Box and lid are two unions on two plates
- **WHEN** a hinged box prints the body and the lid as separate flat prints
- **THEN** the body and the lid are two unions on two different plates, both part
  of the same model

#### Scenario: Print-in-place hinge is two unions on one plate
- **WHEN** both leaves of a hinge print together in one job
- **THEN** they are two distinct unions sharing one `plate`, and the kinematic
  check still treats them as two separate rigid bodies

---

### Requirement: The whole model is one assembly

The kinematic fixed set for a moving union SHALL be every other union in the model;
the plan SHALL NOT require an explicit assembly grouping. A model SHALL be treated
as a single assembled product for collision purposes.

#### Scenario: Fixed set is all other unions
- **WHEN** a union is declared as the moving member of a joint
- **THEN** the check holds every other union in the model fixed without the plan
  enumerating them

---

### Requirement: Blocks are authored in their use pose

A block SHALL be authored in its use (assembled, articulable) pose, and its `dof`
ranges and `interfaces` SHALL be expressed in that frame. The kinematic sweep zero
SHALL correspond to the block's authored use pose. The print pose SHALL be a
downstream concern (mesh analysis for strength and support) and SHALL NOT affect
the use pose, the declared ranges, or the kinematic check.

#### Scenario: Sweep zero is the authored use pose
- **WHEN** a joint block is placed by the planner
- **THEN** a swept value of `required_range[0]` corresponds to the block's authored
  use pose, with no separate "modeled flat vs closed" convention

#### Scenario: Print orientation does not change declared motion
- **WHEN** mesh analysis later reorients a union for printing
- **THEN** the union's declared range and the kinematic check are unaffected,
  because the check runs in assembled (use) coordinates
