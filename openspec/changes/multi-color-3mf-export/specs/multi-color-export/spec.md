## ADDED Requirements

### Requirement: Unions may be grouped into one multi-body slicer object

A `unions` entry in `BUILD_PLAN.json` MAY carry an optional `object` string. Unions that
share the same `object` value SHALL be exported as the bodies (parts) of a single slicer
object. Unions without `object` SHALL each remain their own object, exactly as before
this change. A member with no `plate` of its own and no part-level `plate` SHALL default
to the `object` id as its plate, so a group lands on one plate without extra fields.
Plan validation SHALL reject a plan in which the members of one `object`
come from different parts or resolve to different plates, and SHALL reject an `object`
group with fewer than two members.

#### Scenario: Two unions form one object
- **WHEN** a part declares `unions: [{id: "body", object: "knob", filament: 1}, {id: "ring", object: "knob", filament: 2}]`
- **THEN** the plan validates and `body` and `ring` are exported as two parts of one object, named from the part's `description` like any other 3MF object, with parts named `body` and `ring`

#### Scenario: Members from different parts are rejected
- **WHEN** two unions share `object: "knob"` but are declared by different parts
- **THEN** plan validation reports a structured error naming the object and both parts

#### Scenario: Members on different plates are rejected
- **WHEN** two unions share an `object` but declare different `plate` values
- **THEN** plan validation reports a structured error naming the object and both plates

#### Scenario: Single-member group is rejected
- **WHEN** exactly one union carries `object: "knob"`
- **THEN** plan validation reports a structured error naming the object

#### Scenario: Plans without the fields are unchanged
- **WHEN** no union declares `object` or `filament`
- **THEN** validation and export behave exactly as before this change

### Requirement: Unions may declare a filament slot

A `unions` entry MAY carry an optional integer `filament` >= 1, the 1-based filament
slot (extruder number) the slicer prints that union with. The exporter SHALL NOT check
`filament` against any printer or slicer slot count; an out-of-range slot is left to the
slicer to surface.

#### Scenario: Non-positive filament is rejected
- **WHEN** a union declares `filament: 0`
- **THEN** schema validation rejects the plan

#### Scenario: Large slot numbers pass through
- **WHEN** a union declares `filament: 9`
- **THEN** the plan validates and `9` is written as that body's extruder

### Requirement: Grouped objects are written in the Bambu project-3MF layout

For each `object` group, `model.3mf` SHALL contain one root `<object>` whose `<components>`
reference one sub-object per member union. Each member's mesh SHALL be written to its
own `3D/Objects/object_<n>.model` file and referenced via the 3MF production extension
`p:path`, with the production namespace declared and listed in `requiredextensions` on
the root model, and a `3D/_rels/3dmodel.model.rels` relationship for each object file.
`Metadata/model_settings.config` SHALL contain an `<object>` entry for the group with one
`<part>` per member (id = the component's sub-object id, `subtype="normal_part"`), each
carrying `name` metadata (the union id) and, when the member declares `filament`, an
`extruder` metadata entry with that value. Members SHALL keep their relative assembled
pose in the written components and SHALL share the group's print orientation.

#### Scenario: Per-part extruder is written
- **WHEN** a model with `body` (filament 1) and `ring` (filament 2) in one `object` is built with `--formats 3mf`
- **THEN** `Metadata/model_settings.config` has one `<object>` with two `<part>` entries whose `extruder` metadata are `1` and `2`

#### Scenario: Member meshes live in separate object files
- **WHEN** the same model is built
- **THEN** the root model's grouped object holds only `<components>`, and each referenced mesh is in its own `3D/Objects/object_<n>.model` with zero non-manifold edges

#### Scenario: Ungrouped union with a filament
- **WHEN** an ungrouped union declares `filament: 3`
- **THEN** it is written in the same component layout as a one-member group, and its `model_settings.config` `<object>` entry carries `extruder` metadata `3` (the importer reads a single-volume object's extruder from the object, not the part)

#### Scenario: Plain unions stay inline
- **WHEN** a union declares neither `object` nor `filament`
- **THEN** it is written as an inline single-mesh object exactly as before this change

### Requirement: The 3MF identifies itself as a Bambu project file

`model.3mf` SHALL carry `Application` metadata starting with `BambuStudio-`, so that both
OrcaSlicer and Snapmaker Orca treat it as a project 3MF and apply its plate and extruder
assignments.

#### Scenario: Generator string
- **WHEN** any model is built with `--formats 3mf`
- **THEN** the root model's `<metadata name="Application">` value starts with `BambuStudio-`
