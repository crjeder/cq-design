# keep-out-zones Specification

## Purpose

Let a part's script declare named 3D regions that other geometry in the model must not intrude
into -- e.g. tool clearance for a screwdriver boss, or airflow space in front of a vent -- so the
quality gate can catch intrusions that would otherwise pass silently.

## Requirements

### Requirement: A part's script may declare named keep-out zones

A part's script `result` MAY include a reserved `"keep_out"` key alongside (or instead of) any real
union keys. Its value SHALL be a mapping from zone name to `Workplane`, following the same
`name -> Workplane` shape already used for a multi-union `result`. A zone's name SHALL double as its
human-readable reason (a note-to-self), matching the existing convention where a union id also
serves as its description. `"keep_out"` SHALL be a reserved name: no union anywhere in the model
SHALL be permitted to declare `keep_out` as its own union `id`.

#### Scenario: Single zone declared alongside a real union
- **WHEN** a part's script sets `result` to `{"enclosure": wp, "keep_out": {"screwdriver_clearance_boss1": wp_zone}}`
- **THEN** `enclosure` is treated as that part's union, and `screwdriver_clearance_boss1` is
  registered as a keep-out zone owned by that part

#### Scenario: Multiple zones from one part
- **WHEN** a part's script `result["keep_out"]` maps two names to two solids
- **THEN** both are registered as distinct, independently named zones owned by that part

#### Scenario: Reserved name cannot be a union id
- **WHEN** a part declares a union whose `id` is `keep_out`
- **THEN** plan validation reports an error naming the reserved-word conflict

---

### Requirement: The reserved key is exempt from union declaration

A part declaring `unions` in the plan SHALL NOT be required to list `keep_out` among its declared
union ids, and the presence of a `"keep_out"` key in the script's `result` SHALL NOT trigger the
"result keys must match declared unions" check that applies to real unions.

#### Scenario: keep_out key present without being declared
- **WHEN** a part declares `unions: [{id: "leafA"}, {id: "leafB"}]` and its script `result` is
  `{"leafA": wp_a, "leafB": wp_b, "keep_out": {"zone1": wp_z}}`
- **THEN** validation passes; `keep_out` is not compared against the declared `unions` list

#### Scenario: Part with no declared unions may still declare keep_out
- **WHEN** a single-union part's script `result` is `{"result": wp}` merged with a top-level
  `"keep_out"` mapping (i.e. `result = {<part_id>: wp, "keep_out": {...}}`)
- **THEN** the part's single union is resolved normally and its keep-out zones are registered,
  without requiring the part to declare a `unions` array

---

### Requirement: A zone inherits its declaring part's assembled pose

Each keep-out zone SHALL be transformed by the same pose applied to its declaring part's real
unions: the part's `placement`, or its derived mate-chain pose when the part is reached via a
`joints` mate chain. A zone anchored flush against a feature of its declaring part SHALL therefore
move rigidly with that part.

#### Scenario: Zone follows a placed part
- **WHEN** a part declares a non-identity `placement` and its script emits a `keep_out` zone
- **THEN** the zone's geometry is transformed by that same `placement` before any check consumes it

#### Scenario: Zone follows a mated part
- **WHEN** a part's pose is derived via `mate_chain.compute_mate_poses` rather than an authored
  `placement`
- **THEN** the part's declared keep-out zones use that same derived pose

---

### Requirement: Keep-out zones are excluded from every export, plate, and sweep path

A keep-out zone SHALL NOT be written to the 3MF or STL deliverables, SHALL NOT be assigned a plate,
and SHALL NOT participate in the kinematic sweep as a moving or a fixed body. It exists solely to be
consumed by the keep-out validation check.

#### Scenario: Zone absent from 3MF
- **WHEN** a model containing a declared keep-out zone is exported
- **THEN** the 3MF contains no object corresponding to that zone

#### Scenario: Zone absent from STL output
- **WHEN** a model containing a declared keep-out zone is exported with STL requested
- **THEN** no `<zone>.stl` is produced and no plate STL includes the zone's geometry

#### Scenario: Zone is not swept as a fixed body
- **WHEN** the kinematic check sweeps a moving union against every other union in the model
- **THEN** declared keep-out zones are not among the fixed bodies checked for collision
