# model-export Specification

## Purpose

Define how the assembly of a whole model is written: one assembled-pose STL per union and per
keep-out zone plus a provenance manifest, the source of truth for the whole-model checks.
User-facing model files (3MF, plate STLs, STEP/OBJ/IGES/SCAD) are produced by `build.py`
(see `build-script`).
## Requirements
### Requirement: Export writes a provenance manifest alongside the STLs

The exporter SHALL write a provenance manifest into the STL output directory recording,
for every exported union and every exported keep-out zone, the id of the part script that
produced it and that script's provenance stamp, plus the export's timestamp. The manifest
SHALL be written on every export run, unconditionally, so a consumer never has to special-
case "manifest not yet written" for a project that has been exported at least once since
this mechanism was introduced.

#### Scenario: Manifest is written alongside per-union STLs
- **WHEN** the model exports its per-union assembled-pose STLs
- **THEN** a manifest file also appears in the STL output directory, naming every exported
  union and the provenance stamp of the script that produced it

#### Scenario: Manifest covers keep-out zones too
- **WHEN** a part declares keep-out zones and the model is exported
- **THEN** the manifest also records an entry per zone, keyed by declaring part id and zone
  name, carrying that part's script's provenance stamp

### Requirement: Assembled-pose meshes for the kinematic check are preserved

The exporter SHALL produce one assembled-pose per-union mesh per union, in the union's `placement` pose, as the source of truth consumed by the whole-model checks. These meshes SHALL NOT be used as user deliverables, and producing print-pose deliverables SHALL NOT alter them.

#### Scenario: Print-pose deliverables do not disturb the check meshes
- **WHEN** `build.py` delivers print-pose files
- **THEN** the per-union assembled-pose meshes consumed by the checks are still written in each union's `placement` pose

#### Scenario: Deliverable STL is not copied from the assembly output
- **WHEN** `build.py --formats stl` runs while the assembly directory is current
- **THEN** `<union>.stl` is exported in print pose rather than copied from the assembly directory

### Requirement: Placement and orientation transforms do not serialize the shape

The placement helper `placement.apply_cq` SHALL apply rotations and translations
directly through the OCCT kernel (`BRepBuilderAPI_Transform` on the shape's underlying
`TopoDS_Shape`, with the kernel copy flag), and SHALL NOT route the transform through any
operation that pickles or `copy.deepcopy`s the shape. This helper positions a union into
the assembly pose and applies its recommended print orientation for the model export.
The behavior SHALL hold regardless of whether `cq_warehouse.extensions` has monkeypatched
`Shape._apply_transform`/`Shape.copy`, so transforms never trigger a `BinTools`
serialization round-trip. The composed transform SHALL preserve the existing
`placement` convention: rotations are applied in listed order about axes through the
origin, then the translation, and an absent or empty placement is the identity.

#### Scenario: Transform of patch-affected geometry does not deep-copy

- **WHEN** `cq_warehouse.extensions` is imported (its global `Shape` patch active) and a
  union's geometry is transformed by `apply_cq` for placement or print orientation
- **THEN** the transform is applied without entering the patched `Shape.copy` /
  `copy.deepcopy`, no `BinTools` write/read round-trip occurs, and the export does not
  raise `BinTools_ShapeSet::ReadGeometry` / `BRep_PointRepresentation` errors

#### Scenario: Transform result matches the placement convention

- **WHEN** a placement with one or more `rotate` steps and a `translate_mm` is applied
  via `apply_cq`
- **THEN** the resulting pose is identical to the same placement composed by
  `placement.to_matrix` (rotations in listed order about the origin, then translation)

#### Scenario: Identity placement is unchanged

- **WHEN** `apply_cq` is called with an absent or empty placement
- **THEN** the workplane is returned unchanged, with no transform applied

### Requirement: Optional progress callback

`write_assembly` (in `write_assembly.py`) SHALL accept an optional keyword-only `progress` callable taking one string, default `None`. When supplied, it SHALL be called with a `[k/N] <step> <id>` line for each part loaded and each per-union STL written, each phase counted separately. When `None`, it SHALL produce no progress output. The files written and the returned dict SHALL NOT depend on whether `progress` is supplied.

#### Scenario: Callback receives per-phase lines

- **WHEN** `write_assembly` is called with a recording callback on a plan with two parts and three unions
- **THEN** the callback receives two part-loading lines numbered `[1/2]` and `[2/2]` and three union-STL lines numbered `[1/3]` to `[3/3]`

#### Scenario: No callback

- **WHEN** `write_assembly` is called without `progress`
- **THEN** nothing is printed and the files written are identical to a call with a callback

#### Scenario: JSON CLI unchanged

- **WHEN** `write_assembly` is run as a CLI
- **THEN** stdout is one JSON document (`union_stls`, `keep_out_stls`, `manifest`, `pose_findings`) and contains no progress lines

### Requirement: write_assembly writes only the assembly for checks

The assembly step SHALL be the module `write_assembly.py` with entry point `write_assembly`. It SHALL write, into the STL directory, one assembled-pose STL per union, one assembled-pose STL per keep-out zone, and the provenance manifest. It SHALL NOT write `model.3mf`, plate STLs, or STEP/OBJ/IGES/SCAD files, and SHALL NOT accept a `formats` argument. No `model_export` module or `export_model` function SHALL remain.

#### Scenario: Only assembly files are written

- **WHEN** `write_assembly` runs on a plan with two unions and one keep-out zone
- **THEN** the STL directory holds two union STLs, one keep-out STL and the manifest
- **AND** no `model.3mf` or `plate_*.stl` exists

### Requirement: 3MF writer welds vertices and reports non-manifold edges
The 3MF writers in `exporters/threemf_multi.py` SHALL weld tessellation vertices that coincide to six decimal places into one shared index per physical vertex, keeping first-seen vertex order, so every interior edge of a closed solid is used by exactly two triangles. `write_named_3mf` and `write_single_3mf` SHALL return the number of edges used by other than two triangles in the written index topology, computed from the in-memory welded arrays without re-reading the file. `count_nonmanifold_edges(path)` SHALL remain available as an independent from-file check.

#### Scenario: Closed solid writes zero non-manifold edges
- **WHEN** `write_named_3mf` is called with a closed box
- **THEN** it returns 0
- **AND** `count_nonmanifold_edges` on the written file also returns 0

#### Scenario: Deliverable guard uses the writer's count
- **WHEN** `deliverables.py` writes `model.3mf`
- **THEN** it raises RuntimeError if the writer's returned count is non-zero
- **AND** it does not re-open the written file to count edges

### Requirement: Multi-material 3MF
A 3MF export of a plan with more than one resolved material SHALL record each body's filament slot (extruder) so Bambu Studio / OrcaSlicer open it with filaments pre-assigned. A plan
with a single material SHALL export as before.

#### Scenario: Two-material export
- **WHEN** two unions resolve to different slots
- **THEN** the 3MF carries two distinct extruder assignments (an explicit union `filament` wins over the assigned slot)

#### Scenario: STL and STEP unchanged
- **WHEN** the same plan is exported as STL or STEP
- **THEN** output is identical to a single-material plan

