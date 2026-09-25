## Why

A finished design ships as a full uv project: `lib/` (mesh, export, orientation, placement, exporters, blocks), `build/build.py`, a heavy `pyproject.toml` (trimesh, matplotlib, scipy, networkx, lxml, cq-warehouse), and a lockfile. A user who only wants to tweak a parametric part in their own CadQuery environment has to dig the part script out of that tree and work out which helper modules it needs. TODO.md tracks this as "a minimal deliverable for a parametric part -- just the code, not the full `/lib`".

## What Changes

- New `src/export_standalone.py`: for each part script in `build/`, writes `standalone/<part_id>.py` plus only the helper modules that script imports (`cq_verify`, `cq_compat`, `blocks`), resolved with `ast`. A part that imports only `cadquery` ships as a lone file.
- The `standalone/` directory gets a minimal `pyproject.toml` (cadquery only) and a short `README.md` listing how to run each script and change its `# PARAMETERS`.
- Phase 4 delivery writes `standalone/` on every delivery and reports it next to the existing outputs. The full uv project bundle is unchanged.

## Capabilities

### New Capabilities
- `standalone-part-export`: per-part minimal deliverable, part script plus only the helper modules it imports, with a cadquery-only environment.

### Modified Capabilities
None. The plate-regeneration bundle (`self-contained-build-environment`) is unchanged; `standalone/` is additive.

## Impact

- New: `src/export_standalone.py`, `tests/test_export_standalone.py`.
- Edited: `skill/phase4_deliver.md` (step + layout), `reference/scripts.md`, `CLAUDE.md` file layout, `src/skill_permissions.json`, `TODO.md`.
- No change to `run_cadquery_model.py`'s JSON contract, the quality gate, or `bundle_project.py`.
