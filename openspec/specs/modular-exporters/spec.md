# Modular Exporters

## Purpose

Defines requirements for the `exporters/` module: how format conversion works, which formats are supported, and how the module stays extensible.

## Requirements

### Requirement: Exporters derive all formats from the CadQuery result object, not a cached STL
The `exporters/` module SHALL import the model script, extract the `result` variable, and produce each requested output format from that live CadQuery object. No pre-existing STL SHALL be used as the source for format conversion.

#### Scenario: Request STL and STEP from same model
- **WHEN** `run_exporters("model.py", ["stl", "step"], output_dir)` is called
- **THEN** both files are produced from the same CadQuery `result` object in one import of `model.py`

#### Scenario: Script missing `result` variable
- **WHEN** the model script does not assign a top-level `result` variable
- **THEN** exporter raises `ExportError` with message naming the missing variable and the script path

---

### Requirement: Supported formats at launch are STL, 3MF, STEP, OBJ, IGES, SCAD
The system SHALL support the following export formats via `run_exporters`:

| format | method | notes |
|--------|--------|-------|
| `stl`  | `cq.exporters.export(result, path)` | primary print format |
| `step` | `cq.exporters.export(result, path)` | for CAD editing |
| `3mf`  | trimesh in-memory conversion | Bambu/Prusa slicer format |
| `obj`  | trimesh in-memory conversion | mesh exchange |
| `iges` | `cq.exporters.export(result, path)` | legacy CAD exchange |
| `scad` | mesh-based fallback: temp STL + `import()` wrapper | not parametric |

#### Scenario: 3MF export
- **WHEN** `run_exporters("model.py", ["3mf"], output_dir)` is called
- **THEN** a valid `.3mf` file is produced at `output_dir/model.3mf`

#### Scenario: SCAD export limitation documented
- **WHEN** `run_exporters("model.py", ["scad"], output_dir)` is called
- **THEN** a `.scad` file is produced containing `import("model.stl");` and a comment noting the output is mesh-based and not parametric

---

### Requirement: Exporter module is extensible without modifying existing files
Adding a new format SHALL require only adding a new file `exporters/<format>.py` and registering it in `exporters/__init__.py`. No other files SHALL need modification.

#### Scenario: Adding FreeCAD FCStd export
- **WHEN** `exporters/freecad.py` is added with a `export(result, path)` function and registered
- **THEN** `run_exporters("model.py", ["fcstd"], output_dir)` produces a `.fcstd` file without changes to any other exporter file

---

### Requirement: STL is not surfaced to the LLM during the iteration loop
The wrapper (`run_cadquery_model.py`) SHALL write any intermediate STL to a temp directory. The STL path SHALL NOT appear in the JSON output returned to the LLM. The `stls` and `stl` fields in the JSON contract SHALL be `null` / `[]` during iteration and populated only when the exporter is explicitly invoked for delivery.

#### Scenario: Normal iteration run
- **WHEN** the wrapper runs a part script during the orchestration loop
- **THEN** the JSON output has `"stl": null` and `"stls": []`; geometry facts are available via the `geometry` field

#### Scenario: Explicit preview request
- **WHEN** the LLM requests a preview render during iteration via `--preview`
- **THEN** a preview PNG is rendered and its path appears in `preview`; the underlying temp STL path still does not appear
