# build-script Specification

## Purpose

Defines the self-contained `build.py` that the skill delivers into the working
directory's `build/` folder. The script lets a user regenerate all deliverable
artifacts (`model.3mf`, per-union and per-plate STLs) in print orientation from
`BUILD_PLAN.json` and the per-part scripts, without re-invoking the skill, and
reports results with a CI-usable exit code.

## Requirements

### Requirement: A runnable build script is delivered into the build directory

The skill SHALL place a self-contained, runnable `build.py` into the `build/`
subdirectory of the current working directory during the Build phase. The script
SHALL be produced from a single template stored in the skill's `src/` directory;
the skill SHALL copy that template into `build/build.py`, substituting the absolute
path to the skill's `src/` directory so the copied script can import the shared
tooling (`blocks`, `model_export`, `print_orientation`, `mesh_io`) without the skill
being re-invoked.

#### Scenario: build.py is copied into the working directory build dir

- **WHEN** the skill runs the Build phase in a working directory
- **THEN** a runnable `build/build.py` exists in that working directory
- **AND** its skill-`src` import path is set to the absolute `src/` directory of the
  installed skill, not a placeholder token

#### Scenario: Template is the single source of truth

- **WHEN** the build script template is changed in the skill's `src/`
- **THEN** subsequent skill runs copy the updated template into `build/build.py`
  (the script body is not authored inline per run)

### Requirement: build.py regenerates all plates in print orientation

When executed, `build/build.py` SHALL read `BUILD_PLAN.json` and resolve a print
orientation for each union: it SHALL reuse the skill's accepted `orientations.json` (when
that file is present alongside the part scripts) so the regenerated plates match the ones
the skill delivered, and SHALL otherwise compute the recommended orientation per union
(reusing the skill's print-orientation tooling, honoring each part's `load` hint and the
plan's `overhang_max_deg`). It SHALL then regenerate the deliverable artifacts —
`model.3mf`, one STL per union, and one fused STL per multi-union plate — with each object
written in its resolved print orientation, reusing the shared model-export tooling rather
than reimplementing export logic.

#### Scenario: Running build.py rebuilds the deliverables

- **WHEN** a user runs `python build/build.py` in a directory containing
  `BUILD_PLAN.json` and the per-part scripts
- **THEN** `model.3mf` and the per-union and per-plate STLs are regenerated with each
  object in its resolved print orientation

#### Scenario: Accepted orientations are reused when present

- **WHEN** `orientations.json` (the skill's accepted per-union orientations) sits next to
  the part scripts
- **THEN** `build.py` writes the plates in those accepted orientations rather than
  recomputing them, so the regenerated plates match the delivered ones

#### Scenario: Re-run after editing a part script

- **WHEN** a user edits a `build/<part_id>.py` script and re-runs `build/build.py`
- **THEN** the regenerated plates reflect the edited geometry without the skill being
  re-invoked

#### Scenario: Print orientation honors the plan

- **WHEN** a part declares a `load` hint in `BUILD_PLAN.json`
- **THEN** that union's print orientation is chosen using the declared load direction
  and the plan's `overhang_max_deg`; when no `load` hint is present the orientation is
  chosen from a geometry-inferred load axis

### Requirement: build.py reports results and signals failure via exit code

`build/build.py` SHALL print a human-readable summary listing, per union, the chosen
print orientation and the output paths it wrote. It SHALL exit zero only when all plates
are regenerated successfully and non-zero when any union fails to load, orient, or export,
naming the failing union, so the script is usable in shells and CI.

#### Scenario: Successful run reports orientations and exits zero

- **WHEN** all unions are regenerated successfully
- **THEN** the script prints each union's chosen orientation and output paths
- **AND** exits with status zero

#### Scenario: Failure exits non-zero

- **WHEN** a union's part script cannot be loaded or its export fails
- **THEN** the script reports the failing union and exits with a non-zero status
