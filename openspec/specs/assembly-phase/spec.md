# Assembly Phase

## Purpose

Defines requirements for the assembly phase: how multiple validated parts are combined
into the final assembled model declaratively from each union's `placement` via the
model-level export, rather than from a hand-written fused CadQuery script.

## Requirements

### Requirement: Multi-part models are assembled declaratively from placement

The build pipeline SHALL combine multiple validated parts into the final assembled
model declaratively, from each union's `placement`, via the model-level export
(`model_export.py`). The pipeline SHALL NOT generate a hand-written fused CadQuery
assembly script, and SHALL NOT write `build/assembly.py`. Each part SHALL remain a
separately authored and separately validated single-body union; assembled position is
determined solely by each union's `placement` (identity when absent), not by code that
unions or cuts parts into one body.

#### Scenario: No fused assembly script is generated
- **WHEN** a plan has more than one part and every part passes the part loop
- **THEN** the pipeline produces the assembled model via `model_export.py` and does not
  generate or write a fused `build/assembly.py` CadQuery script

#### Scenario: Assembled position comes from placement
- **WHEN** a two-part model declares a `lid` union with a `placement`
- **THEN** the assembled model positions the lid by applying its placement, with no
  hand-coded positions in any assembly script

#### Scenario: No assembly prompt template exists
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no `claude -p` assembly-script
  generation step

---

### Requirement: Assembly phase emits the model export, not a fused body

The assembly phase SHALL run the model-level export to produce the assembled-pose
artifacts: a named-object 3MF (each union a separately named object carrying its
`plate` metadata), one assembled-pose STL per union, and one fused STL per plate that
holds more than one union. The whole-model kinematic check SHALL consume the per-union
assembled STLs from this export. The quality gate SHALL operate on the individual union
part scripts (per-rigid-body DFM, geometry, and overhang), not on a fused multi-union
script.

#### Scenario: Model export produces per-union assembled STLs
- **WHEN** the assembly phase runs for a multi-part model
- **THEN** `model_export.py` emits one assembled-pose STL per union plus the named-object
  3MF, and the kinematic check reads the per-union STLs from that export

#### Scenario: Quality gate runs per union for multi-part models
- **WHEN** the quality gate runs for a multi-part model
- **THEN** its DFM/geometry/overhang checks operate on each union's own part script, and
  the whole-model kinematic check runs once over the exported per-union assembled STLs
