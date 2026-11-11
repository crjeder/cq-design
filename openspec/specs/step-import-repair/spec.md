# step-import-repair Specification

## Purpose
TBD - created by archiving change step-import-repair. Update Purpose after archive.
## Requirements
### Requirement: Checked STEP/BREP import

`blocks.import_solid(path, max_volume_deviation=0.01)` SHALL import a `.step`/`.stp` file with `cq.importers.importStep`, or a `.brep` file with `cq.Shape.importBrep`, and return a `cq.Workplane` holding the solid. It SHALL check the imported shape against the grader's criterion. The shape passes when `BRepCheck_Analyzer.IsValid()` is true, it contains a solid, and `mesh_gate.mesh_gate_error` returns `None`. Face area SHALL NOT be part of the check. A shape that passes SHALL be returned unchanged, with nothing printed, and SHALL NOT be healed.

#### Scenario: Valid file
- **WHEN** a script calls `import_solid` on a valid STEP box
- **THEN** it returns the box unchanged, with the same volume and face count, and prints nothing

#### Scenario: Zero-area face that passes the grader
- **WHEN** the imported solid has a face below 1e-3 mm² but passes BRepCheck and the mesh gate (CADGenBench 242, 246, 248)
- **THEN** it is returned unchanged and nothing is printed

#### Scenario: Valid file is never healed
- **WHEN** a valid input that the heal would break is imported (CADGenBench 206, 215, 238)
- **THEN** it is returned unchanged

#### Scenario: Other extension
- **WHEN** `import_solid` is called on `part.stl`
- **THEN** it raises `ValueError` naming the accepted extensions

### Requirement: Staged ShapeFix heal

When the check fails, `import_solid` SHALL heal the shape in up to three stages. Each stage SHALL work on the previous stage's output, and the check SHALL run after each:

1. `wire`: `ShapeFix_Shape` with precision 1e-7 and max tolerance `heal_tol`. Its wire tool SHALL have `FixTailMode`, `FixNotchedEdgesMode`, `FixSmallMode`, `FixSelfIntersectionMode` and `FixNonAdjacentIntersectingEdgesMode` on, max tail width `heal_tol` and max tail angle 0.1 rad.
2. `small_edges`: `ShapeFix_Wireframe` at precision `heal_tol` with `ModeDropSmallEdges`, then `FixSmallEdges` and `FixWireGaps`.
3. `small_faces`: `ShapeFix_FixSmallFace` at precision and max tolerance `heal_tol`.

`heal_tol` SHALL be `max(0.1 mm, the shape's largest edge tolerance)`. After each stage, the stage output SHALL be written to STEP and read back, and the check SHALL run on the reloaded shape. The grader only ever sees the reloaded shape, and in-memory BRepCheck can disagree with it in both directions. Stages SHALL chain on the in-memory output. `import_solid` SHALL return the in-memory shape of the first stage whose reload passes the check and is within the volume limit (re-exporting the reload is not guaranteed valid). An OCC exception in a stage SHALL end the heal with `step_unrepairable`.

#### Scenario: Wire spike
- **WHEN** a face's outer wire has a zero-width tail and BRepCheck reports `UnorientableShape` (CADGenBench 202)
- **THEN** stage `wire` removes it, and the returned solid passes BRepCheck and the mesh gate after a STEP round trip

#### Scenario: Zero-area faces that break the mesh
- **WHEN** the solid is BRep-valid but its zero-area faces make the mesh gate report an edge shared by 4 triangles (CADGenBench 250)
- **THEN** the heal returns a solid that passes the mesh gate, with a volume change below 0.01 %

#### Scenario: Sub-tolerance edge
- **WHEN** a B-spline face has a 1.6e-6 mm edge whose tolerance is 0.019 mm (CADGenBench 217)
- **THEN** the heal returns the reloaded solid of a later stage that passes the check, even though the in-memory BRepCheck of that stage still flags a face

#### Scenario: Fold plus slivers
- **WHEN** a blend face has a folded lobe and the solid also has five zero-area faces (CADGenBench 240)
- **THEN** the full heal returns a solid that passes the check, with a volume change below 0.05 %

### Requirement: Volume-deviation limit

A healed result SHALL be accepted only if `abs(V_healed - V_imported) / V_imported <= max_volume_deviation`. `max_volume_deviation` SHALL be a fraction, default `0.01` (1 %), settable per call.

#### Scenario: Heal within the limit
- **WHEN** a heal changes the volume by 0.005 % and the limit is the default
- **THEN** the healed solid is returned

#### Scenario: Stricter limit
- **WHEN** the same heal runs with `max_volume_deviation=0.0`
- **THEN** the heal is rejected and `step_unrepairable` is raised

### Requirement: Unrepairable import is a typed error

When no heal stage yields a result that passes the check within the volume limit, `import_solid` SHALL raise `RuntimeError("[cq-verify:step_unrepairable:<file name>] <detail>")`. The detail SHALL name the remaining BRepCheck statuses or mesh-gate reason, the stages tried, and the volume delta of the last stage. The wrapper SHALL map it to an error of type `step_unrepairable`, with a hint saying that the input file is invalid and that the region must be rebuilt rather than edited.

#### Scenario: Heal exhausted
- **WHEN** a solid is missing a face, so no stage closes it
- **THEN** the run fails with one `step_unrepairable` error naming the file and the remaining statuses

### Requirement: Repairs are reported

A successful heal SHALL print one stdout line, `[cq-design:step-repair] ` followed by a JSON object with `file`, `strategy` (the heal stages applied, in order), `heal_tol_mm` and `volume_delta_pct`.

#### Scenario: Repair line
- **WHEN** stage 1 heals a file
- **THEN** the wrapper's `stdout` contains one `[cq-design:step-repair]` line whose `strategy` is `["wire"]`
