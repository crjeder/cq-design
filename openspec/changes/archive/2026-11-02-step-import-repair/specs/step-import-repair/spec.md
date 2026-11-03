## ADDED Requirements

### Requirement: Checked STEP/BREP import

`blocks.import_solid(path, max_volume_deviation=0.01)` SHALL import a `.step`/`.stp` file with `cq.importers.importStep`, or a `.brep` file with `cq.Shape.importBrep`, and return a `cq.Workplane` holding the solid. It SHALL run a validity check on the imported shape. The shape passes when `BRepCheck_Analyzer.IsValid()` is true and no face has an area below 1e-3 mm². A shape that passes SHALL be returned unchanged, with nothing printed.

#### Scenario: Valid file
- **WHEN** a script calls `import_solid` on a valid STEP box
- **THEN** it returns the box unchanged, with the same volume and face count, and prints nothing

#### Scenario: Other extension
- **WHEN** `import_solid` is called on `part.stl`
- **THEN** it raises `ValueError` naming the accepted extensions

### Requirement: Topological repair ladder

When the check fails, `import_solid` SHALL apply these repairs in order. Each SHALL work on the previous one's output, and the check SHALL run after each:

1. Remove faces with area below 1e-3 mm², sew at 1e-2, and rebuild the solid.
2. Remove the faces BRepCheck flags with `BRepAlgoAPI_Defeaturing`.
3. Replace each flagged face with a `BRepOffsetAPI_MakeFilling` patch over its outer-wire edges, then sew at 1e-2.

It SHALL return the first result that passes the check and is within the volume limit. It SHALL NOT use tolerance-only fixes.

#### Scenario: Zero-area faces
- **WHEN** the imported solid has two faces below 1e-3 mm² and is otherwise valid (CADGenBench 250)
- **THEN** rung 1 removes them and the returned solid passes the check

#### Scenario: Self-intersecting face
- **WHEN** BRepCheck flags one face with a self-intersecting wire and rung 1 does not clear it (CADGenBench 217)
- **THEN** rung 2 defeatures that face and the returned solid passes the check

### Requirement: Volume-deviation limit

A repaired result SHALL be accepted only if `abs(V_repaired - V_imported) / V_imported <= max_volume_deviation`. `max_volume_deviation` SHALL be a fraction, default `0.01` (1 %), settable per call.

#### Scenario: Repair within the limit
- **WHEN** a repair changes the volume by 0.005 % and the limit is the default
- **THEN** the repaired solid is returned

#### Scenario: Stricter limit
- **WHEN** the same repair runs with `max_volume_deviation=0.00001`
- **THEN** the repair is rejected and `step_unrepairable` is raised

### Requirement: Unrepairable import is a typed error

When no rung yields a result that passes the check within the volume limit, `import_solid` SHALL raise `RuntimeError("[cq-verify:step_unrepairable:<file name>] <detail>")`. The detail SHALL name the remaining BRepCheck statuses and the volume delta of the last rung. The wrapper SHALL map it to an error of type `step_unrepairable`, with a hint saying that the input file is invalid and that the region must be rebuilt rather than edited.

#### Scenario: Ladder exhausted
- **WHEN** every rung leaves a flagged face (CADGenBench 240)
- **THEN** the run fails with one `step_unrepairable` error naming the file and the remaining statuses

### Requirement: Repairs are reported

A successful repair SHALL print one stdout line, `[cq-design:step-repair] ` followed by a JSON object with `file`, `strategy` (the rungs applied), `faces_removed` and `volume_delta_pct`.

#### Scenario: Repair line
- **WHEN** rung 1 repairs a file
- **THEN** the wrapper's `stdout` contains one `[cq-design:step-repair]` line whose `strategy` lists rung 1
