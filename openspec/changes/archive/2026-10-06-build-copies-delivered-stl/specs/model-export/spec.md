## MODIFIED Requirements

### Requirement: Optional progress callback

`write_assembly` (formerly `export_model`, in `write_assembly.py`, formerly `model_export.py`) SHALL accept an optional keyword-only `progress` callable taking one string, default `None`. When supplied, it SHALL be called with a `[k/N] <step> <id>` line for each part loaded and each per-union STL written, each phase counted separately. When `None`, it SHALL produce no progress output. The files written and the returned dict SHALL NOT depend on whether `progress` is supplied.

#### Scenario: Callback receives per-phase lines

- **WHEN** `write_assembly` is called with a recording callback on a plan with two parts and three unions
- **THEN** the callback receives two part-loading lines numbered `[1/2]` and `[2/2]` and three union-STL lines numbered `[1/3]` to `[3/3]`

#### Scenario: No callback

- **WHEN** `write_assembly` is called without `progress`
- **THEN** nothing is printed and the files written are identical to a call with a callback

#### Scenario: JSON CLI unchanged

- **WHEN** `write_assembly` is run as a CLI
- **THEN** stdout is one JSON document (`union_stls`, `keep_out_stls`, `manifest`, `pose_findings`) and contains no progress lines

## ADDED Requirements

### Requirement: write_assembly writes only the assembly for checks

The assembly step SHALL be the module `write_assembly.py` with entry point `write_assembly`. It SHALL write, into the STL directory, one assembled-pose STL per union, one assembled-pose STL per keep-out zone, and the provenance manifest. It SHALL NOT write `model.3mf`, plate STLs, or STEP/OBJ/IGES/SCAD files, and SHALL NOT accept a `formats` argument. No `model_export` module or `export_model` function SHALL remain.

#### Scenario: Only assembly files are written

- **WHEN** `write_assembly` runs on a plan with two unions and one keep-out zone
- **THEN** the STL directory holds two union STLs, one keep-out STL and the manifest
- **AND** no `model.3mf` or `plate_*.stl` exists

## REMOVED Requirements

### Requirement: Unions export as separately named objects in an assembled 3MF

**Reason**: 3MF generation is a user-facing deliverable and moves to `build.py` / `deliverables.py`.
**Migration**: See `build-script` requirement "build.py writes named-object 3MF, STL and extra formats".

### Requirement: STL export is a single-body fallback

**Reason**: Plate STL generation moves to `build.py` / `deliverables.py`; the per-union assembled STLs are still written by `write_assembly`.
**Migration**: See `build-script` requirement "build.py writes named-object 3MF, STL and extra formats".

### Requirement: Per-union export in additional formats

**Reason**: Extra formats are user-facing and are selected through `build.py --formats`.
**Migration**: Use `build.py --formats step|obj|iges|scad` or `/cq-design:build <format>`.
