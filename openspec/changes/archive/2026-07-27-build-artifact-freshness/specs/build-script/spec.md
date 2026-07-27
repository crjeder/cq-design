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
