## MODIFIED Requirements

### Requirement: build.py accepts an export format option

`build.py` SHALL accept `--formats LIST`, a comma-separated list drawn from `3mf`, `stl`,
`step`, `obj`, `iges`, `scad`, `estampo`. When omitted it SHALL default to the single format
`slicer.preferred_format` from `profile.json`. It SHALL write only the listed formats, except
that `estampo` also writes the STLs its `estampo.toml` references. It
SHALL write into the single `--out` directory (default `<project root>/out`) and SHALL NOT
accept `--stl-out`. An unsupported key SHALL exit non-zero with a message listing the
supported keys. The reported results SHALL list the files written for each format.

#### Scenario: Default invocation

- **WHEN** `build.py` runs without `--formats` and the profile's preferred format is `3mf`
- **THEN** `out/model.3mf` is written and no STL, STEP, OBJ, IGES or SCAD file is written

#### Scenario: Several formats requested

- **WHEN** `build.py --formats 3mf,step` runs
- **THEN** `out/model.3mf` and a `<union-id>.step` per union are written to `out/` and no STL is written

#### Scenario: estampo requested

- **WHEN** `build.py --formats estampo` runs
- **THEN** `out/estampo.toml` and the STLs it references are written to `out/`

#### Scenario: Unsupported format

- **WHEN** `build.py --formats dxf` runs
- **THEN** it exits non-zero and names the supported keys

#### Scenario: Removed option is rejected

- **WHEN** `build.py --stl-out x` runs
- **THEN** it exits non-zero with an unrecognized-argument error
