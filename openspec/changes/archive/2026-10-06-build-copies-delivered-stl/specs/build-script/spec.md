## MODIFIED Requirements

### Requirement: build.py regenerates all plates in print orientation

When executed, `build/build.py` SHALL read `BUILD_PLAN.json` and resolve a print
orientation for each union: it SHALL reuse the skill's accepted `orientations.json` (when
that file is present alongside the part scripts) so the regenerated plates match the ones
the skill delivered, and SHALL otherwise compute the recommended orientation per union
(reusing the bundled print-orientation tooling, honoring each part's `load` hint and the
plan's `overhang_max_deg`). Before reusing an accepted entry, it SHALL check that entry's
provenance stamp (when present) against the current contents of the union's source part
script; on a mismatch it SHALL recompute that entry's orientation instead of reusing the
stale one, and SHALL report in its summary output which entries were recomputed and why. An
accepted entry carrying no provenance stamp SHALL be reused unconditionally, matching the
behavior before provenance stamping existed. It SHALL then write the requested formats (see
"build.py accepts an export format option") with each object in its resolved print
orientation where the format has one, reusing the bundled deliverables tooling rather than
reimplementing export logic.

#### Scenario: Running build.py rebuilds the deliverables

- **WHEN** a user runs `uv run python build/build.py` in a directory containing
  `BUILD_PLAN.json` and the per-part scripts
- **THEN** the preferred-format deliverable is regenerated with each object in its resolved
  print orientation

#### Scenario: Accepted orientations are reused when present and current

- **WHEN** `orientations.json` sits next to the part scripts and each entry's provenance
  stamp still matches its source script
- **THEN** `build.py` writes the plates in those accepted orientations rather than
  recomputing them

#### Scenario: Stale accepted orientation is recomputed, not reused

- **WHEN** a part script is edited after `orientations.json` was written, so that union's
  accepted entry's provenance stamp no longer matches the current script
- **THEN** `build.py` recomputes that union's orientation instead of reusing the stale
  entry, and its summary output names the recomputed union and states that the source
  script changed

#### Scenario: Unstamped accepted entry is reused unconditionally

- **WHEN** an accepted orientation entry carries no provenance stamp
- **THEN** `build.py` reuses it without attempting a staleness comparison

#### Scenario: Re-run after editing a part script

- **WHEN** a user edits a `build/<part_id>.py` script and re-runs `uv run python build/build.py`
- **THEN** the regenerated output reflects the edited geometry without the skill being
  re-invoked

#### Scenario: Print orientation honors the plan

- **WHEN** a part declares a `load` hint in `BUILD_PLAN.json`
- **THEN** that union's print orientation is chosen using the declared load direction
  and the plan's `overhang_max_deg`; when no `load` hint is present the orientation is
  chosen from a geometry-inferred load axis

### Requirement: build.py accepts an export format option

`build.py` SHALL accept `--formats LIST`, a comma-separated list drawn from `3mf`, `stl`,
`step`, `obj`, `iges`, `scad`. When omitted it SHALL default to the single format
`slicer.preferred_format` from `profile.json`. It SHALL write only the listed formats. It
SHALL write into the single `--out` directory (default `<project root>/out`) and SHALL NOT
accept `--stl-out`. An unsupported key SHALL exit non-zero with a message listing the
supported keys. The reported results SHALL list the files written for each format.

#### Scenario: Default invocation

- **WHEN** `build.py` runs without `--formats` and the profile's preferred format is `3mf`
- **THEN** `out/model.3mf` is written and no STL, STEP, OBJ, IGES or SCAD file is written

#### Scenario: Several formats requested

- **WHEN** `build.py --formats 3mf,step` runs
- **THEN** `out/model.3mf` and a `<union-id>.step` per union are written to `out/` and no STL is written

#### Scenario: Unsupported format

- **WHEN** `build.py --formats dxf` runs
- **THEN** it exits non-zero and names the supported keys

#### Scenario: Removed option is rejected

- **WHEN** `build.py --stl-out x` runs
- **THEN** it exits non-zero with an unrecognized-argument error

## ADDED Requirements

### Requirement: build.py writes named-object 3MF, STL and extra formats

`build.py` SHALL write, per requested format:

- `3mf`: `model.3mf` in which each union is a separately named object, in its print
  orientation when one is resolved, else its assembled pose. Names SHALL derive from the
  part's `description` (whitespace collapsed, control characters removed, length bounded),
  falling back to the part `id` when empty, and SHALL be disambiguated with the part `id`
  suffix only for colliding names. Each object SHALL carry its `plate` tag as metadata.
  Distinct unions SHALL NOT be fused, and the written 3MF SHALL have no non-manifold edges.
- `stl`: one STL per union in the assembled pose and one fused print-pose STL per plate
  holding more than one union.
- `step`, `obj`, `iges`, `scad`: one `<union-id>.<ext>` per union in the assembled pose.
  Keep-out zones SHALL NOT be written in any user-facing format.

#### Scenario: Each union is a named 3MF object

- **WHEN** a model with multiple unions is built with `--formats 3mf`
- **THEN** each union is a separately named object with its plate in metadata, and no two are fused

#### Scenario: Per-union STL plus fused plate STL

- **WHEN** a plate holds two print-in-place unions and `--formats stl` runs
- **THEN** one STL per union and one fused STL for the plate are written

#### Scenario: Keep-out zones are not deliverables

- **WHEN** a part declares a keep-out zone and any format is built
- **THEN** no file for the zone appears in `--out`

### Requirement: build.py copies the last-phase per-union STLs when current

When `stl` is requested and the assembly manifest in `<project root>/stl` exists, no union's
`source_script_hash` or `print_rotate` is stale against the current part scripts and
resolved orientations, and every wanted `stl/<union-id>.stl` exists, `build.py` SHALL copy
those STLs to `--out` instead of regenerating them (no copy when `--out` is that same
directory). Otherwise it SHALL regenerate them. Plate STLs, 3MF and extra formats SHALL
always be generated. The summary SHALL state whether per-union STLs were copied or
regenerated.

#### Scenario: Fresh assembly STLs are copied

- **WHEN** the assembly STLs are current and `build.py --formats stl` runs
- **THEN** the per-union STLs in `out/` are copies of those in `stl/` and the union geometry is not re-exported
- **AND** the summary says they were copied

#### Scenario: Stale assembly STLs are regenerated

- **WHEN** a part script changed after the assembly step wrote its manifest
- **THEN** `build.py --formats stl` regenerates the per-union STLs and says so
