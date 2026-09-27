## Why

`fem_check.py` currently meshes and solves the part's STEP geometry as a fully solid, isotropic volume — equivalent to assuming 100% infill. Real FDM parts are mostly sparse infill (`printer_profile.json`'s `motion.infill_density`) inside a solid perimeter shell whose thickness is governed by a single Orca "wall loops" setting; the solid-volume solve therefore overstates the part's real stiffness and strength. A shell-only solve — mesh and solve only the wall thickness the slicer will actually lay down solid, treating the interior as void — gives a defensible conservative (lower-bound) stability estimate instead, since it ignores infill's real but harder-to-model contribution rather than pretending the interior is fully solid.

## What Changes

- `fem_check.py` builds and solves a hollow-shell volume (wall thickness only) instead of the full solid volume, using `gmsh.model.occ.addThickSolid(volumeTag, [], offset)` on the imported STEP solid (confirmed available in the pinned `gmsh` version — verified empirically, not assumed).
- Shell thickness is one uniform value applied to every triangle (vertical and horizontal alike, no face-normal split) — the same simplification the "wall loops" setting itself makes.
- Shell thickness is sourced from `printer_profile.json`'s `constraints.wall_min_mm` (via the existing `walls = max(2, ceil(wall_min_mm / nozzle_mm))` formula already in `quality_gate.py`), not a hardcoded constant.
- **BREAKING** (schema addition, not removal): `printer_profile_schema.json` gains a `top_bottom_layers` field (analogous role to `wall_min_mm`, but for top/bottom shell layer count) so the top/bottom shell thickness (`top_bottom_layers * motion.layer_height_mm`) is a real, author-declared setting instead of the literal `4` currently hardcoded in `quality_gate.py`'s `build_recipe`.
- `build_recipe` (`quality_gate.py`) reads `top_bottom_layers` from the profile instead of hardcoding it, and reads `motion.layer_height_mm` directly instead of re-deriving `nozzle_mm * 0.5`.
- `fem_check.py`'s result gains a warning field, emitted when the wall thickness (`wall_min_mm`-derived) and the top/bottom shell thickness (`top_bottom_layers * layer_height_mm`) differ by more than 25% — flagging that the "treat every triangle the same thickness" simplification is questionable for this profile.

## Capabilities

### New Capabilities

(none — this extends existing capabilities)

### Modified Capabilities

- `fem-stress-advisor`: the solve changes from full-solid to hollow-shell (wall-thickness-only) geometry; a new profile-mismatch warning is added to the result contract.
- `printer-profile-config`: schema gains `top_bottom_layers`; `motion.layer_height_mm` becomes an authoritative input to recipe generation instead of being re-derived.

## Impact

- `src/fem_check.py`: `mesh_step` (build hollow-shell volume before meshing), `run_fem_check` (source shell thickness from the plan/profile, compute and emit the 25% mismatch warning).
- `src/printer_profile_schema.json`, `src/printer_profile.default.json`: add `top_bottom_layers` (default `4`, matching current hardcoded behavior).
- `src/printer_profile_validate.py`: validate/write-back the new field.
- `src/quality_gate.py`: `build_recipe` reads `top_bottom_layers` and `motion.layer_height_mm` from the profile instead of a hardcoded literal and a re-derived value.
- `tests/test_printer_profile_validate.py`: coverage for the new `top_bottom_layers` field.
- `tests/test_fem_check.py`: coverage for the hollow-shell solve and the 25% mismatch warning.
- `pyproject.toml`'s `fem` dependency group is unaffected (still `gmsh`, `scikit-fem`); no new dependency.
