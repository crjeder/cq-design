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

---

### Requirement: A part script is executed at most once per content and print pose per process
`exporters._load_result` SHALL memoize its result for the lifetime of the process, keyed by the script's absolute path, a hash of its bytes, and the `print_rotate` value. A load that must observe execution (a hooked load that wraps CadQuery operations) SHALL skip the lookup (`fresh=True`) and store its result, so later loads reuse it.

#### Scenario: Repeat load of an unchanged script
- **WHEN** `_load_result(script, None)` is called twice in one process and the file is unchanged
- **THEN** the script body executes once and both calls return the same `result`

#### Scenario: Script edited between loads
- **WHEN** the script file's bytes change between two `_load_result` calls
- **THEN** the second call re-executes the script and returns the new `result`

#### Scenario: Different print pose
- **WHEN** `_load_result` is called with two different `print_rotate` values
- **THEN** the script executes once per distinct value

#### Scenario: Hooked load
- **WHEN** a check loads with `fresh=True`
- **THEN** the script executes and its wrapped CadQuery calls are recorded even if a cached result exists, and a later plain load returns that result without executing again

---

### Requirement: Delivery reuses the shim's loaded result when the pose matches
When `run_cadquery_model.py --deliver` runs without `--print-rotate`, the requested formats SHALL be written from the result the shim subprocess already loaded, without a second import of the script. With `--print-rotate`, delivery SHALL still export the authored-frame result.

#### Scenario: Deliver without rotate
- **WHEN** `--deliver --formats stl,3mf` is given and no `--print-rotate`
- **THEN** the script executes once in total and `stls` and `threemfs` in the JSON output are populated as before

#### Scenario: Deliver with rotate
- **WHEN** `--deliver` is given with `--print-rotate`
- **THEN** the delivered files are the authored-frame geometry, identical to today's output

---

### Requirement: Edge-treatment and feature-presence share one hooked load
The quality gate SHALL record fillet/chamfer edges and cut/union tool bounding boxes in a single script execution when the part's print rotate is None or identity, and SHALL produce the same findings as running the two checks separately.

#### Scenario: Unrotated part
- **WHEN** the gate runs both stages for a part with no rotate
- **THEN** the script executes once for hook recording and both stages' findings equal their standalone results

#### Scenario: Rotated part
- **WHEN** the part has a non-identity rotate
- **THEN** feature-presence records in the authored frame from its own load, so its findings are unchanged
