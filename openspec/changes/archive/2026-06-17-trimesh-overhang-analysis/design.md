## Context

The quality gate (`src/quality_gate.py`) is the final pipeline phase. It already
contains `_analyze_stl`, which loads the exported STL with trimesh and emits
issues for non-watertight geometry and a single "worst overhang angle" warning.
The project docs (`CLAUDE.md`) still describe the gate as aggregating
"scad-analyzer + orca-check" MCP results, implying an external OrcaSlicer
dependency that the code does not actually use. The orca-check and scad-analyzer
MCPs exist in the user's environment but are not invoked by the gate.

The current overhang check is too thin to replace orca-check: it reports only the
worst angle, with no extent (how much of the model overhangs), no location (where),
and no support classification that downstream consumers can act on. `measure_stl.py`
already demonstrates the trimesh + numpy idioms for face centroids and location
reporting used elsewhere in the codebase.

## Goals / Non-Goals

**Goals:**
- Make `_analyze_stl` a genuine, self-contained replacement for orca-check's
  overhang signal: area, worst-region location, and support classification.
- Keep all analysis in-process (trimesh + numpy only), deterministic, and offline.
- Preserve the existing issue contract (`source`/`severity`/`type`/`message`/`hint`)
  so the fix-prompt and print-recipe stages need no changes.
- Remove stale orca-check / scad-analyzer references from the docs.

**Non-Goals:**
- Replicating slicer-level checks (bed adhesion, seam placement, real support
  volume, bridging feasibility). Those require an actual slicer and are out of
  scope; this is a geometry-only approximation.
- Auto-reorienting the model to minimize overhangs.
- Changing the fix-round loop, print recipe schema, or wrapper DFM checks.

## Decisions

**Decision: Geometry-only overhang analysis instead of slicer integration.**
Compute overhang angle per face from face normals (`arcsin(-nz)` from horizontal),
threshold against `overhang_max_deg`. Rationale: no external binary, runs anywhere
the existing trimesh dep is installed, fully deterministic. Alternative considered:
shelling out to OrcaSlicer CLI (what orca-check does) — rejected because it
reintroduces the external dependency this change removes and is non-deterministic
across slicer versions.

**Decision: Report area + worst-region location, not just worst angle.**
Sum the areas (`tm.area_faces`) of flagged faces for `overhang_area_mm2`; pick the
flagged face with the max angle and report its centroid (mean of its three
vertices) as `location_xyz_mm`. Rationale: gives Claude an actionable "where and
how much" instead of a scalar. Alternative: cluster flagged faces into regions and
report each — rejected as over-engineered for the gate's needs; a single worst
region plus total area is sufficient signal.

**Decision: Keep `overhang_exceeded` as a warning, not an error.**
Overhangs are printable with supports; flagging them as errors would block clean
passes for legitimately support-using designs. Warning severity surfaces them in
the fix prompt without failing the gate on its own. This matches current behavior.

**Decision: Reuse trimesh primitives already loaded; no new dependency.**
`tm.face_normals`, `tm.area_faces`, `tm.triangles`/`tm.vertices` cover all needed
quantities. No new packages.

## Risks / Trade-offs

- [Geometry-only check misses real printability failures orca-check would catch
  (adhesion, bridging, support collisions)] → Document explicitly as a non-goal in
  docs and the print recipe wording; the gate remains a geometry approximation, not
  a slicing guarantee.
- [Overhang angle from face normals is mesh-tessellation sensitive; curved
  surfaces produce many near-threshold faces] → Threshold strictly greater than
  `overhang_max_deg` and report aggregate area so a few borderline facets do not
  dominate; worst-angle/location stay meaningful.
- [Removing doc references could orphan the orca-check MCP expectation for users
  who relied on it] → The MCP remains available in the environment; only the gate's
  stated pipeline drops it. Note in docs that printability validation via a real
  slicer is optional and external.

## Migration Plan

1. Harden `_analyze_stl` (area, location, support classification) keeping the
   issue shape backward compatible (only additive fields on the overhang issue).
2. Update/extend tests to cover the new fields and classification.
3. Purge orca-check / scad-analyzer references from `CLAUDE.md`, align `SKILL.md`
   and `README.md` wording.

No data migration; no rollback concern beyond reverting the commit.

## Open Questions

- None blocking. Future option: optionally re-enable a slicer-backed check behind
  a flag if real printability validation is later required.
