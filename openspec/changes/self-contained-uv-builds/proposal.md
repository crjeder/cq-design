## Why

The skill delivers `build/build.py` into the user's working directory, but it is not
self-contained: it imports the shared tooling (`blocks`, `model_export`,
`print_orientation`, `mesh_io`, `exporters`) from an absolute `SKILL_SRC` path baked
in at copy time, and must run inside the skill's own Python environment. If the skill
is moved, uninstalled, or run on another machine, `build.py` breaks. The user wants
the delivered working directory to stand on its own as a uv-managed virtual environment
that contains everything needed to regenerate artifacts, with the uv workflow (including
the build command) documented in `build.py`'s docstring and the README.

## What Changes

- **Scaffold the working directory as a standalone uv project.** During the Build
  phase the skill SHALL write a `pyproject.toml` (pinning the runtime dependencies the
  tooling needs: cadquery, trimesh, numpy, lxml, matplotlib, scipy, networkx,
  cq-warehouse) and a `.python-version` into the working directory, and SHALL produce a
  committed `uv.lock` so the environment is reproducible.
- **Make the delivered tooling self-contained.** The shared tooling that `build.py`
  imports SHALL be available inside the working directory's own environment without the
  skill being installed (no dependency on a `SKILL_SRC` absolute path). The mechanism
  (vendoring the modules vs. depending on an installable package) is decided in
  design.md.
- **Run the build under uv.** `build.py` SHALL be runnable with
  `uv run python build/build.py` from the working directory after `uv sync`, using the
  project's own environment. **BREAKING**: `build.py` no longer carries a `SKILL_SRC`
  placeholder substituted with the skill's `src/` path, and no longer requires the
  skill's environment to be on `PYTHONPATH`.
- **Document the uv usage.** `build.py`'s module docstring SHALL document the uv
  workflow (`uv sync`, then `uv run python build/build.py`), and the README's
  "Regenerating the 3MF / STL files" section SHALL be updated to describe the
  self-contained uv project and the build command instead of the baked-`src` model.

## Capabilities

### New Capabilities
- `self-contained-build-environment`: the skill scaffolds the working directory as a
  standalone uv project (pyproject.toml, .python-version, pinned uv.lock, and the
  bundled build tooling) so a user can regenerate all deliverable artifacts with
  `uv run python build/build.py` on any machine that has uv, without the skill installed.

### Modified Capabilities
- `build-script`: the delivered `build.py` no longer imports the shared tooling from a
  baked `SKILL_SRC` absolute path or runs in the skill's environment; it runs inside the
  working directory's own uv environment and imports the bundled tooling. Its docstring
  documents the uv workflow and build command.

## Impact

- Tooling/templates: `src/build_template.py` (drop `SKILL_SRC` bootstrap, document uv
  workflow in docstring), plus whatever the skill copies/scaffolds into `build/`.
- Skill workflow: `SKILL.md` Build phase (scaffold uv project + bundle tooling +
  `uv sync` + `uv lock` instead of substituting `SKILL_SRC`).
- Docs: `README.md` "Regenerating the 3MF / STL files" section.
- Specs: `build-script` (modified delta), new `self-contained-build-environment` spec.
- Existing `uv-environment` spec (skill repo environment) is unaffected; this change
  concerns the delivered working directory's environment.
