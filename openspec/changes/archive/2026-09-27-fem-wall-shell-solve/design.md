## Context

`fem_check.py::mesh_step` currently imports the part's STEP solid with
`gmsh.model.occ.importShapes` and tet-meshes it as-is (`fem_check.py:162-191`) — the whole
volume, solved isotropically at the material's bulk `E_mpa`/`nu`
(`material_properties.json`). Real FDM parts are a solid perimeter shell (thickness set by
Orca's single "wall loops" count) around sparse infill (`motion.infill_density`, e.g. 0.15).
Solving the full solid volume is equivalent to assuming 100% infill — it overstates
stiffness and strength.

`printer_profile.json` already declares `constraints.wall_min_mm` (the wall thickness the
slicer targets) but has no equivalent field for top/bottom shell thickness: `top_bottom_layers`
is a bare literal (`4`) inside `quality_gate.py::build_recipe`, and that same function
re-derives `layer_height_mm` as `nozzle_mm * 0.5` instead of reading the profile's own
`motion.layer_height_mm` when present.

Verified empirically (scratch script against the pinned `gmsh>=4.12,<5`) that
`gmsh.model.occ.addThickSolid(volumeTag, excludeSurfaceTags, offset)` — OCC's
`BRepOffsetAPI_MakeThickSolid` — accepts an **empty** `excludeSurfaceTags` list and returns a
new, fully closed hollow volume of wall thickness `offset`, with no opening required. This
was the open question from the exploration that unlocks the shell-only solve without an
approximate tet-distance-classification workaround.

## Goals / Non-Goals

**Goals:**
- Solve only the part's wall-thickness shell (uniform thickness on every face, vertical and
  horizontal alike), as a documented conservative lower bound on stiffness/strength,
  ignoring infill's real contribution rather than pretending the interior is solid.
- Source that thickness from `printer_profile.json`'s `constraints.wall_min_mm`, not a
  hardcoded constant.
- Make `top_bottom_layers` a real, author-declared profile setting instead of a hardcoded
  literal buried in `quality_gate.py`, so the new mismatch warning compares two settings the
  user actually controls.
- Warn in the FEM result when the wall thickness and the top/bottom shell thickness
  (`top_bottom_layers * layer_height_mm`) differ by more than 25%, since the uniform-thickness
  simplification gets less defensible as they diverge.

**Non-Goals:**
- Not modeling infill directly (no lattice/homogenized-infill material model). Ignoring it
  entirely is the deliberate simplification this change makes.
- Not solving for a required wall thickness / wall-loop count (a separate, later capability;
  this change only changes what geometry the existing single solve runs against).
- Not handling multi-solid STEP parts (multi-union parts) specially — see Open Questions.
- Not auto-selecting mesh size relative to the new (thinner) shell geometry. Mesh size stays
  an explicit author-provided argument per the existing `fem-stress-advisor` requirement; the
  author is responsible for choosing a size that resolves the shell (see Risks).

## Decisions

### Build a real hollow-shell volume via `addThickSolid` + `cut`, not tet-distance classification

**Chosen:** after `importShapes`, capture the returned solid volume tag(s); for each,
call `gmsh.model.occ.addThickSolid(tag, [], -wall_thickness_mm)` (**negative** offset) to
get the inward-offset cavity solid, then `gmsh.model.occ.cut([(3, tag)], cavity,
removeTool=True)` to subtract it from the original, leaving the wall material as a single
closed hollow solid whose outer boundary matches the part; `cut` consumes both inputs, so
nothing extra needs removing before meshing.

**Correction during implementation:** a bare `addThickSolid(tag, [], +offset)` with an
empty excluded-face list does **not** hollow the solid in place, contrary to what the
exploration's empirical check (a same-session scratch script) seemed to show. Verified
against the pinned gmsh version with a controlled bounding-box check: a positive offset
returns a new solid uniformly grown *outward* from the original; a negative offset returns
one shrunk *inward* -- either way it's an offset duplicate, not "the wall material between
old and new surface." The original exploration's check only confirmed that a second volume
tag appeared after the call, never checked its bounding box, and coincidentally proceeded
to remove the original volume before meshing -- which produced a mesh with several hundred
nodes unreferenced by any tet (all-zero stiffness rows), an exact matrix singularity that
surfaced only when the solve-path tests ran (`skfem.utils.MatrixRankWarning: Matrix is
exactly singular`, `fi_max`/`fi_p99` coming back `nan`), not as a `mesh_step` exception.
The cut-based two-step construction was verified (same technique: compare bounding boxes,
then mesh and check every node is tet-referenced) to reproduce the original part's exact
outer boundary with zero orphaned nodes.

As a second, independent safety net (regardless of root cause), `mesh_step` now compacts
its returned `points`/`tets`/`boundary_tris` to only tet-referenced nodes -- an
unreferenced node is an exact stiffness-matrix singularity, not merely an ill-conditioned
one, so this is cheap insurance against any other geometry or gmsh-version quirk producing
the same failure mode silently (no exception, `status: "ok"`, `nan` failure indices).

**Alternative considered:** mesh the full solid as today, then classify tets by distance to
the boundary mesh (`trimesh.proximity`) and exclude interior tets from the stiffness
assembly. Rejected now that `addThickSolid` is confirmed available: it meshes the true
shell geometry from the start (better element quality at the true wall boundary, no wasted
interior tets, no post-hoc filtering/renumbering step), at the cost of one more OCC boolean
during import.

### Thickness = `constraints.wall_min_mm` directly, not a wall-loop-count re-derivation

**Chosen:** the shell offset passed to `addThickSolid` is `constraints.wall_min_mm` as-is.

**Alternative considered:** re-derive via `quality_gate.py`'s `walls = max(2, ceil(wall_min_mm
/ nozzle_mm))` and multiply back out by `line_width_mm`. Rejected: that formula exists to
report a whole-loop-count recipe field for the slicer; `wall_min_mm` is already the physical
thickness value the constraint represents, and re-deriving it through a ceiling+line-width
round-trip can only move it further from the declared value, not closer.

### One uniform thickness for every face — no vertical/horizontal split

**Chosen:** `addThickSolid` with a single scalar `offset` applied to the whole solid,
matching Orca's own single "wall loops" setting (the setting this change models does not
distinguish vertical walls from top/bottom shells either).

**Alternative considered:** split by face normal (vertical faces get `wall_min_mm`,
near-horizontal faces get `top_bottom_layers * layer_height_mm`) via two `addThickSolid`
passes or per-face offsets. Rejected as unnecessary complexity for a lower-bound advisor;
the 25% mismatch warning (below) covers the case where the simplification is questionable,
without requiring the solver itself to model two thicknesses.

### `top_bottom_layers` becomes a real (optional) profile field, alongside `wall_min_mm`

**Chosen:** add `constraints.top_bottom_layers` (integer, minimum 1) to
`printer_profile_schema.json`, following the existing `constraints.bridge_max_mm` pattern
(`printer-profile-config` spec's "Optional bridge length limit" requirement): optional,
defaults to `4` when absent, existing profiles without it still validate.
`quality_gate.py::build_recipe` reads it via `constraints.get("top_bottom_layers", 4)`
instead of the current hardcoded `4`.

**Alternative considered:** fold it into the existing `motion` block instead. Rejected:
`motion`'s own requirement ("Partial motion block is rejected, not defaulted") requires all
seven fields together or none — `top_bottom_layers` is a shell-geometry constraint like
`wall_min_mm`, not a toolhead-speed parameter, and forcing it into `motion` would mean a
profile with a `motion` block but no explicit `top_bottom_layers` fails validation instead of
defaulting, breaking every existing profile with a `motion` block today.

### `layer_height_mm` read from `motion` when present, else the existing `nozzle * 0.5` fallback

**Chosen:** `build_recipe` uses `plan.get("motion", {}).get("layer_height_mm", nozzle *
0.5)` — preserves current behavior for profiles without a `motion` block (matches by
construction, since the default profile's `motion.layer_height_mm` happens to equal `nozzle
* 0.5`), but stops silently overriding a profile that declares a different value.

**Alternative considered:** always re-derive as `nozzle * 0.5`, leaving the declared
`motion.layer_height_mm` unread. Rejected: this is the exact drift this change's own mismatch
warning would otherwise be comparing against a wrong number.

### 25% mismatch is computed once per `fem_check.py` run and returned as a result field, never blocks

**Chosen:** `pct_diff = abs(wall_mm - topbot_mm) / max(wall_mm, topbot_mm)`; when `> 0.25`,
add a `"thickness_mismatch_warning"` field to the result naming both values and the percent
difference. Computed the same way in both `fem_check.py` (for the warning) and
`quality_gate.py::build_recipe` (for the recipe's own `top_bottom_layers`/`layer_height_mm`
fields), so the two never quote different top/bottom-thickness numbers for the same plan.

**Alternative considered:** raise the warning as a separate CLI exit code or stage. Rejected:
`fem-stress-advisor`'s existing "the advisor never blocks" requirement — this is additional
information in the same never-blocking JSON result, not a new gate.

## Risks / Trade-offs

- **Mesh resolution through a thin shell** → thin-shell elements at coarse mesh sizes give
  too few tets through the thickness for P1 tets to resolve bending accurately (the
  linear-tet locking problem gets worse as the solved region gets thinner). Mitigation:
  none automatic in this change (mesh size stays author-controlled, per existing
  `fem-stress-advisor` requirement); documented as a sharper version of the existing
  "re-run at a smaller mesh size and compare `fi_p99`" guidance, since the shell is now the
  thinnest feature in the model by construction.
- **`addThickSolid` can fail or produce self-intersecting/degenerate geometry** on parts with
  local features thinner than ~2x the wall thickness (fillets, bosses, thin ribs) → falls
  into the existing "gmsh meshing failed" skip path (`run_fem_check`'s existing
  `except Exception` around `mesh_step`) rather than a new failure mode; no new skip reason
  needed, but this will make some parts skip that previously solved (as a full solid) fine.
  This is an accepted trade-off of shell-only solving, not a bug to fix here.
  → Mitigation: none beyond the existing skip path; flagged for the author via the existing
  skip-reason mechanism.
- **Multi-solid STEP parts** (multi-union parts) → `importShapes` may return more than one
  volume tag; shelling each independently is assumed correct (each body gets its own uniform
  wall) but untested against the existing multi-union contract. → Mitigation: none in this
  change; see Open Questions.
- **Schema addition is technically additive, not breaking** for existing profiles (default
  applies), but any code (outside this change) that reads `quality_gate.py`'s hardcoded `4`
  as a de facto constant loses that assumption once profiles start setting
  `top_bottom_layers` explicitly. → Mitigation: grep for other hardcoded top/bottom-layer
  literals before merging (none currently known outside `build_recipe`).

## Migration Plan

1. Schema + default profile + validator: add `top_bottom_layers` (optional, default 4) —
   backward compatible, no existing profile needs editing.
2. `quality_gate.py::build_recipe`: read `top_bottom_layers` and `motion.layer_height_mm`
   from the profile instead of the hardcoded literal / re-derivation. Verify against
   existing recipe-generation tests that the default profile still produces the same
   `walls`/`layer_height_mm`/`top_bottom_layers` recipe values as before (no observable
   change for the shipped default profile).
3. `fem_check.py::mesh_step`: switch to the hollow-shell volume; `run_fem_check`: source
   the offset from `constraints.wall_min_mm`, compute and attach the mismatch warning.
4. No rollback complexity: this is a pure code/schema change with no persisted state beyond
   `printer_profile.json`, which remains valid before and after.

## Open Questions

- Multi-solid (multi-union) parts: shell each returned volume independently, or restrict this
  capability to single-body parts for now and skip (with a stated reason) otherwise? Left
  for `tasks.md` / implementation to decide against the actual multi-union test fixtures.
- Should the mismatch warning also fire from `quality_gate.py` (e.g., as an advisory note in
  the recipe output), or stay solely in `fem_check.py`'s result? This change adds it only to
  the FEM result, since that's the consumer whose "uniform thickness" assumption it protects.
