## Context

`export_model` does two unrelated jobs. Per part it loads unions and poses them (needed by
every check), writes assembled-pose STLs and the manifest in `stl/` (consumed by kinematic,
plate-clearance and keep-out checks), and also writes the user's `model.3mf`, plate STLs and
extra formats. `build_template.py` calls it again with different dirs. Importers of
`model_export`: `load_part_unions`, `export_model`, name/plate helpers across eight `src/`
modules.

## Goals / Non-Goals

**Goals:**
- One generator of user-facing files (`build.py`), one output dir, formats chosen on demand.
- A module whose name says what it does: the assembly for checks.

**Non-Goals:**
- Changing check inputs (`stl/<id>.stl`, keep-out STLs, manifest format/location).
- Changing orientation resolution or `run_cadquery_model.py --deliver`.

## Decisions

1. **Rename `model_export.py` -> `write_assembly.py`, `export_model` -> `write_assembly`.**
   Keeps `load_part_unions` and the pose helper (public `pose_union`) since checks and builds both
   import them. Returns `union_stls`, `keep_out_stls`, `manifest`, `pose_findings`. Alternative:
   `assembly.py`; rejected, it collides with the `assembly-phase` spec noun and hides that it
   writes files. No compatibility shim: all importers are in-repo and bundled by `bundle_project.py`.
2. **New `deliverables.py`** with `write_deliverables(plan, parts_dir, out, orientations, formats,
   progress)`: `3mf` (named objects, print orientation, plate metadata, non-manifold guard),
   `stl` (per-union assembled STL + fused plate STL in print pose), extras (assembled pose). Moves
   the 3MF naming helpers (`_object_name`, `_dedupe_object_names`) with it. Alternative: put this in
   `build_template.py`; rejected, the template is copied per project and is hard to unit-test.
3. **`--formats` default = preferred_format; one `--out`, default `<root>/out`.** Keeps `stl/`
   (checks, internal) and `out/` (user files) visibly separate; today's root-level `model.3mf`
   and `stl/` mix both roles. Validation: unknown key exits non-zero listing the six keys.
4. **Copy per-union STLs when fresh.** For `stl`, if the `stl/` manifest exists, `stale_ids` and
   `pose_stale_ids` are empty and every `stl/<union>.stl` exists, copy them to `--out`
   (`shutil.copy2`); else regenerate. Plate STLs, 3MF and extras are always generated (print
   pose / not produced by the assembly step).
5. **Skill flow.** Model export step: `plan.py validate` -> `write_assembly.py` (checks need it)
   -> quality gate -> `bundle_project.py` -> `uv sync` -> `uv run python build/build.py`
   (preferred format). Phase 4 lists `out/` instead of `model.3mf` + `stl/`.
6. **`/cq-design:build [format]`** runs `uv run python build/build.py [--formats <format>]` in
   the working directory; it replaces `/cq-design:deliver`. Fails with a pointer to `/cq-design:init`
   or `/cq-design:update` when `build/build.py` is missing.

## Risks / Trade-offs

- [Wide rename touches many modules and specs] -> Mechanical; grep for `model_export` and
  `export_model` must return zero outside `openspec/changes/archive` and this change.
- [Users and docs expecting root `model.3mf`] -> Documented BREAKING; README layout updated.
- [Fresh check trusts hashes, not file contents] -> Same gating as existing freshness checks.
- [`/cq-design:deliver` users] -> Command removed; `/cq-design:build` is the replacement.

## Migration Plan

Land rename + split together; run `/cq-design:update` in existing projects. Rollback is
reverting the commit.

## Open Questions

- Default `--out` of `out/` is a choice; trivial to change to project root if preferred.
