## MODIFIED Requirements

### Requirement: The working directory is scaffolded as a standalone uv project

During the Build phase the skill SHALL scaffold the working directory as a self-contained
uv project so the user can regenerate artifacts without the skill installed. When absent, it SHALL write
a `pyproject.toml` pinning the runtime dependencies the build tooling imports (cadquery,
trimesh, numpy, lxml, matplotlib, pillow, scipy, networkx, and the `cq-warehouse` git
source) with `requires-python = ">=3.10,<3.13"`, and SHALL write a `.python-version`
selecting a CadQuery-compatible interpreter (3.10-3.12). An existing `pyproject.toml` or
`.python-version` SHALL NOT be overwritten; if it differs from the template the skill SHALL
print a note saying so.

#### Scenario: Build phase writes the project files

- **WHEN** the skill runs the Build phase in a working directory with no `pyproject.toml`
- **THEN** a `pyproject.toml` declaring the runtime dependencies and `requires-python =
  ">=3.10,<3.13"` exists in that working directory
- **AND** a `.python-version` selecting a 3.10-3.12 interpreter exists

#### Scenario: Existing pyproject kept

- **WHEN** the Build phase is re-run and `pyproject.toml` already exists with different content
- **THEN** the file is unchanged and a note reports that it differs from the template

#### Scenario: pyproject pins the cq-warehouse git source

- **WHEN** the scaffolded `pyproject.toml` is inspected
- **THEN** it declares `cq-warehouse` under `[tool.uv.sources]` as the same git source used
  by the skill, so the lock resolves to a pinned commit
