## ADDED Requirements

### Requirement: cq_warehouse catalog availability
The skill's Python environment SHALL include `cq_warehouse` so that model scripts can import fastener classes without any additional installation step beyond `pip install -r requirements.txt`.

#### Scenario: User imports a fastener class
- **WHEN** a model script contains `from cq_warehouse.fastener import HexHeadScrew`
- **THEN** the import SHALL succeed when the script is run via `run_cadquery_model.py`

#### Scenario: Missing cq_warehouse
- **WHEN** `cq_warehouse` is not installed and a script tries to import it
- **THEN** `run_cadquery_model.py` SHALL surface the `ModuleNotFoundError` in `stderr` and set `success` to `false`

### Requirement: Fastener parts integrate as CadQuery Solids
Model scripts SHALL be able to instantiate `cq_warehouse` fastener objects and add them to CadQuery Workplanes using standard CadQuery `.add()`, `.union()`, or `.cut()` operations. Scripts SHALL cast fastener objects to `cadquery.Solid` via `Solid(part.wrapped)` before applying any CadQuery transform (translate, rotate, etc.) to avoid constructor incompatibilities in `cq_warehouse` subclasses.

#### Scenario: Fastener added to a model and exported
- **WHEN** a script creates a `HexHeadScrew`, calls `cq.Workplane().box(...).add(bolt)`, and exports the result with `cq.exporters.export()`
- **THEN** `run_cadquery_model.py` SHALL produce a valid STL, report `success: true`, and include geometry in the JSON output

#### Scenario: Fastener used to cut a clearance hole
- **WHEN** a script calls `.cut(bolt)` to subtract bolt geometry from a body
- **THEN** the resulting solid SHALL export successfully and pass the watertight check

### Requirement: SKILL.md cq_warehouse documentation
`SKILL.md` SHALL document the `cq_warehouse` workflow with: available fastener classes, the instantiation pattern (`size`, `length`, `fastener_type`, `simple`), and how to add parts to a Workplane.

#### Scenario: Fastener usage example present
- **WHEN** a developer reads `SKILL.md`
- **THEN** they SHALL find a runnable example showing a fastener imported, instantiated with `simple=True`, and added to a CadQuery body
