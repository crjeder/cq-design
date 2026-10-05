## ADDED Requirements

### Requirement: Per-union export in additional formats

`export_model` SHALL accept a `formats` collection of exporter keys from `step`, `obj`, `iges`, `scad` (default empty), written in addition to the 3MF and STLs, which are always written. For each key it SHALL write one file per union, named `<union-id>.<extension>`, in the assembled pose, using the modular exporter registered for that key, into the STL output directory. Keep-out zones SHALL NOT be written in these formats. The returned dict SHALL contain a `format_files` mapping of format key to a mapping of union id to path. An unsupported key (including `stl` and `3mf`, which are not optional) SHALL raise before any file is written.

#### Scenario: STEP requested

- **WHEN** `export_model` is called with `formats=("step",)` on a plan with two unions
- **THEN** `<union-id>.step` exists for each union in the STL output directory
- **AND** the STEP geometry is in the assembled pose, matching the per-union STL
- **AND** `format_files["step"]` maps each union id to its path
- **AND** `model.3mf`, the per-union STLs and plate STLs are written as before

#### Scenario: Default output unchanged

- **WHEN** `export_model` is called without `formats`
- **THEN** the files written are exactly those written before this change
- **AND** `format_files` is empty

#### Scenario: Unsupported format

- **WHEN** `formats` contains a key that is unknown or is `stl`/`3mf`
- **THEN** export raises an error naming the key and the supported keys
- **AND** no output files are written
