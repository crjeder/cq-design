## ADDED Requirements

### Requirement: A build unit may produce multiple named unions

A part (a build unit -- one script) SHALL be able to produce more than one union. A part MAY declare
an optional `unions` array; each entry SHALL carry a globally-unique union `id` and MAY carry a
`plate`. When `unions` is declared, the part's script `result` SHALL be a mapping from each declared
union `id` to that union's geometry, and each entry SHALL be exported, posed, and kinematically
checked as a distinct union. When `unions` is absent, the part SHALL be a single union whose `id` is
the part id and whose plate is the part's `plate` (the default, unchanged). Union ids SHALL be unique
across the whole model and SHALL form the namespace that `kinematics.moving_union`, plate grouping,
and per-union export all reference. A part's `placement` SHALL apply to every union it produces.

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
  declared union ids
- **THEN** the model export reports a structured error rather than silently dropping or misnaming a
  union

#### Scenario: Duplicate union ids are rejected
- **WHEN** two unions anywhere in the model share an `id` (including a sub-union id colliding with a
  part id)
- **THEN** plan validation fails with an error naming the duplicate
