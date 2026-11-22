## ADDED Requirements

### Requirement: Gate evaluates authored plan probes

The quality gate SHALL evaluate every `probes[]` entry of the part on the part's finished
body in build pose (all unions as one compound), for step scripts and plain part scripts
alike, and SHALL emit one blocking error of type `probe_unmet` per failing probe with
`label`, `kind`, `expected`, `observed`, `message` and `hint`. Probes whose `label` appears in
an `acceptance_bindings[]` entry's `probes` for that part SHALL be skipped (the oracle stage
checks them). A part with no `probes[]` SHALL not have its body loaded by this stage and SHALL
get no `probe_unmet` issue.

#### Scenario: Wall on the wrong side of its dimension
- **WHEN** a plain part script builds a 2 mm wall offset inward, and the plan has a
  `solid_at` probe 1 mm inside the dimensioned outer face
- **THEN** the gate reports `probe_unmet` with that probe's label, `expected` IN, `observed`
  OUT and severity `error`

#### Scenario: Profile matches
- **WHEN** every authored probe on the part holds on the built body
- **THEN** the gate reports no `probe_unmet`

#### Scenario: Oracle-bound probe
- **WHEN** a failing probe's label is listed in an `acceptance_bindings[]` entry for the part
- **THEN** the gate reports it only as `oracle_unmet`, not as `probe_unmet`

#### Scenario: No probes
- **WHEN** the part has no `probes[]`
- **THEN** the stage emits nothing

### Requirement: Planner derives thin-walled form from section views

The planning prompt SHALL instruct the planner, for a drawing of a thin-walled or sheet-metal
part, to derive the 3D form from the section views before decomposing: for each thickness
dimension, the face it references and the side the material lies on; for each bend, whether
the radius is inside or outside; for each flange, its direction. The planner SHALL record
these in `planning_notes`, and SHALL author for every dimensioned wall face a
`solid_at`/`empty_at` bracket and for every flange a `solid_at` probe near its tip, each
`label` naming the view it comes from.

#### Scenario: Sheet-metal bracket drawing
- **WHEN** the drawing shows a 2 mm bent bracket with a section view dimensioning its outer
  faces
- **THEN** the plan's `planning_notes` states that thicknesses are measured inward from the
  outer faces and the bend radius side, and the part's `probes[]` has a bracket per
  dimensioned face and a flange-tip `solid_at`, each label citing the section view
