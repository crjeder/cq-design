# printable-unit-model Specification

## Purpose

Define how a build plan models a fabricated product as a set of rigid *unions*
grouped into *plates*, each union carrying its pose in a shared assembly pose.
This is the structural source of truth consumed by the model-level export and the
whole-model kinematic check.

## Requirements

### Requirement: Each union declares its assembled placement

Each union SHALL carry an optional `placement` describing its pose in the shared
assembly pose: a `translate_mm` (`[x, y, z]`) and an ordered `rotate` list of
`{axis, angle_deg}` steps (`axis` one of `X`, `Y`, `Z`). Rotations SHALL apply in
listed order, then the translation. An absent `placement` SHALL mean identity (the
union is authored directly in the assembly pose). The placement SHALL be the
single structured source of truth for assembled position, consumed by both the
model-level export and the kinematic check.

#### Scenario: Union without placement is in the assembly pose as authored
- **WHEN** a union omits `placement`
- **THEN** its as-authored geometry is treated as already in the assembly pose

#### Scenario: Placement positions a union in the assembly pose
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

---

### Requirement: A build unit may produce multiple named unions

A part (a build unit -- one script) SHALL be able to produce more than one union. A part MAY declare
an optional `unions` array; each entry SHALL carry a globally-unique union `id` and MAY carry a
`plate`. When `unions` is declared, the part's script `result` SHALL be a mapping from each declared
union `id` to that union's geometry, and each entry SHALL be exported, posed, and kinematically
checked as a distinct union. When `unions` is absent, the part SHALL be a single union whose `id` is
the part id and whose plate is the part's `plate` (the default, unchanged). Union ids SHALL be unique
across the whole model and SHALL form the namespace that `kinematics.moving_union`, plate grouping,
and per-union export all reference. A part's `placement` SHALL apply to every union it produces.

The `result` mapping MAY additionally carry one reserved key, `"keep_out"`, whose value is itself a
`name -> Workplane` mapping of declared keep-out zones (see the `keep-out-zones` capability). This
reserved key is discovered the same way declared union keys are, but is never itself a union: it is
exempt from the declared-`unions` cross-check, is not exported, plated, or swept, and `keep_out`
SHALL NOT be usable as a union `id`.

#### Scenario: Single-union part is the default
- **WHEN** a part declares no `unions` and its script sets `result` to a single `Workplane`
- **THEN** it is one union whose id is the part id and whose plate is the part's `plate`, exactly as
  before this change

#### Scenario: One part produces two unions
- **WHEN** a part declares `unions: [{id: "leafA"}, {id: "leafB"}]` and its script sets `result` to a
  mapping `{"leafA": <wp>, "leafB": <wp>}`
- **THEN** the model exports, poses, and kinematically checks `leafA` and `leafB` as two distinct
  unions produced by the one script

#### Scenario: Union ids are the motion and plate namespace
- **WHEN** a `kinematics` entry names `moving_union: "leafA"` and a plate references a union
- **THEN** they resolve against the union namespace (which includes sub-union ids), not only part ids

#### Scenario: A part's unions may sit on different plates
- **WHEN** a part declares `unions: [{id: "leafA", plate: "p1"}, {id: "leafB", plate: "p2"}]`
- **THEN** `leafA` and `leafB` are grouped onto different plates even though one part produced them

#### Scenario: Result keys must match the declared unions
- **WHEN** a part declares `unions` but its script `result` mapping has keys that differ from the
  declared union ids (ignoring the reserved `keep_out` key, if present)
- **THEN** the model export reports a structured error rather than silently dropping or misnaming a
  union

#### Scenario: Duplicate union ids are rejected
- **WHEN** two unions anywhere in the model share an `id` (including a sub-union id colliding with a
  part id)
- **THEN** plan validation fails with an error naming the duplicate

#### Scenario: The reserved keep_out key is not cross-checked against declared unions
- **WHEN** a part's script `result` includes a `"keep_out"` key whose name does not appear in the
  part's declared `unions` array
- **THEN** no "result keys must match declared unions" error is reported for that key

#### Scenario: keep_out cannot be declared as a union id
- **WHEN** a part's `unions` array declares an entry with `id: "keep_out"`
- **THEN** plan validation fails with an error naming the reserved-word conflict
