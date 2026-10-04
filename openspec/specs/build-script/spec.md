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
SHALL be produced from a single template stored in the skill's `src/` directory; the
skill SHALL copy that template into `build/build.py`. The copied script SHALL import the
shared tooling (`blocks`, `model_export`, `print_orientation`, `mesh_io`, `exporters`)
from the tooling bundled into the working directory by the skill, NOT from an absolute
`SKILL_SRC` path or the installed skill's `src/` directory. The script SHALL run inside
the working directory's own uv environment, with no requirement that the skill be installed
or on `PYTHONPATH`.

#### Scenario: build.py is copied into the working directory build dir

- **WHEN** the skill runs the Build phase in a working directory
- **THEN** a runnable `build/build.py` exists in that working directory
- **AND** it imports its tooling from the bundled files in the working directory, not from
  a `SKILL_SRC` placeholder or the installed skill's `src/` path

#### Scenario: Template is the single source of truth

- **WHEN** the build script template is changed in the skill's `src/`
- **THEN** subsequent skill runs copy the updated template into `build/build.py`
  (the script body is not authored inline per run)

#### Scenario: build.py runs without the skill installed

- **WHEN** the delivered working directory is synced with `uv sync` on a machine that does
  not have the skill installed
- **THEN** `uv run python build/build.py` runs successfully using the working directory's
  own environment and bundled tooling

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
behavior before provenance stamping existed. It SHALL then regenerate the deliverable
artifacts — `model.3mf`, one STL per union, and one fused STL per multi-union plate — with
each object written in its resolved print orientation, reusing the bundled model-export
tooling rather than reimplementing export logic.

#### Scenario: Running build.py rebuilds the deliverables

- **WHEN** a user runs `uv run python build/build.py` in a directory containing
  `BUILD_PLAN.json` and the per-part scripts
- **THEN** `model.3mf` and the per-union and per-plate STLs are regenerated with each
  object in its resolved print orientation

#### Scenario: Accepted orientations are reused when present and current

- **WHEN** `orientations.json` (the skill's accepted per-union orientations) sits next to
  the part scripts and each entry's provenance stamp still matches its source script
- **THEN** `build.py` writes the plates in those accepted orientations rather than
  recomputing them, so the regenerated plates match the delivered ones

#### Scenario: Stale accepted orientation is recomputed, not reused

- **WHEN** a part script is edited after `orientations.json` was written, so that union's
  accepted entry's provenance stamp no longer matches the current script
- **THEN** `build.py` recomputes that union's orientation instead of reusing the stale
  entry, and its summary output names the recomputed union and states that the source
  script changed

#### Scenario: Unstamped accepted entry is reused unconditionally

- **WHEN** an accepted orientation entry carries no provenance stamp (written before this
  mechanism existed, or added by hand)
- **THEN** `build.py` reuses it without attempting a staleness comparison, matching prior
  behavior

#### Scenario: Re-run after editing a part script

- **WHEN** a user edits a `build/<part_id>.py` script and re-runs `uv run python build/build.py`
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

### Requirement: build.py reports progress

`build.py` SHALL print progress to stdout, flushed per line, while building. Each unit of work SHALL be reported as `[k/N] <step> <id>`, where `N` is the number of units in that phase and `k` counts from 1. Phases SHALL be counted separately; no cross-phase percentage SHALL be reported. Unions whose accepted orientation is reused unchanged SHALL NOT be reported in the orientation phase. The existing final summary and the `build failed:` message on stderr SHALL be unchanged.

#### Scenario: Parts loaded

- **WHEN** `build.py` runs on a plan with three parts
- **THEN** it prints `[1/3]`, `[2/3]` and `[3/3]` loading lines, each naming a part id, before the final summary

#### Scenario: Orientation reused

- **WHEN** every union has a fresh accepted orientation in `orientations.json`
- **THEN** no orientation progress lines are printed

#### Scenario: Orientation recomputed

- **WHEN** two unions have no accepted orientation or a stale one
- **THEN** exactly two orientation lines `[1/2]` and `[2/2]` are printed, naming those unions

#### Scenario: Progress is live when piped

- **WHEN** `build.py` stdout is a pipe
- **THEN** each progress line is flushed as it is printed rather than at process exit

#### Scenario: Failure

- **WHEN** a part script fails to load
- **THEN** `build failed: ...` is written to stderr and the exit code is non-zero, as before
