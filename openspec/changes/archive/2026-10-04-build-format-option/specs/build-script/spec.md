## ADDED Requirements

### Requirement: build.py accepts an export format option

`build.py` SHALL accept `--formats LIST`, a comma-separated list of extra exporter keys (`step`, `obj`, `iges`, `scad`), defaulting to none, and SHALL pass it to `export_model`. `model.3mf` and the STLs SHALL always be written. The reported results SHALL list the files written for each requested format, and an unsupported key SHALL exit non-zero with a message listing the supported keys.

#### Scenario: Default invocation

- **WHEN** `build.py` runs without `--formats`
- **THEN** it writes `model.3mf`, the per-union STLs, and the per-plate STLs, as before

#### Scenario: STEP requested

- **WHEN** `build.py --formats step` runs
- **THEN** a `<union-id>.step` file is written for every union, alongside the 3MF and STLs
- **AND** the reported results list those files

#### Scenario: Unsupported format

- **WHEN** `build.py --formats dxf` runs
- **THEN** it exits non-zero and names the supported keys
