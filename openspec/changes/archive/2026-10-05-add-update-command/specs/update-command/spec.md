## ADDED Requirements

### Requirement: Update command re-copies the installed skill tooling into the project

`/cq-design:update` SHALL run `bundle_project.py` against the working directory, copying the installed skill's current `src/` tooling into the project exactly as initial bundling does: `build_template.py` to `build/build.py`, bundled modules and the `blocks` / `exporters` packages to `lib/`, and the permissions/hooks merge into `.claude/settings.local.json`. It SHALL copy unconditionally, whether or not the stamp reports the project current. It SHALL NOT modify part scripts, `BUILD_PLAN.json`, `pyproject.toml`, `install.sh`, or `install.ps1`.

#### Scenario: Tooling refreshed
- **WHEN** `/cq-design:update` runs in a project bundled by an older skill version
- **THEN** `build/build.py` and `lib/` match the installed skill's `src/`, retired bundled files are pruned, and `.bundle_version.json` carries the installed commit

#### Scenario: Copy is unconditional
- **WHEN** `bundle_project.py --check .` would report `current`
- **THEN** the command still copies, so uncommitted skill edits reach the project

#### Scenario: Not a bundled project
- **WHEN** the working directory has neither `lib/` nor `.bundle_version.json`
- **THEN** the command stops and tells the user to run the normal pipeline instead of creating a bundle

#### Scenario: Rebuild is left to the user
- **WHEN** the copy completes
- **THEN** the command reports the new stamp and suggests `uv sync` and `uv run python build/build.py`, without running them
