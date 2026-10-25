## Context

Today `threemf_multi.write_named_3mf` writes one `<object>` per union plus plate metadata
in `Metadata/model_settings.config`. `plan.material` is one enum consumed by `fem_check`,
`quality_gate` (density) and the preview footer. `material_properties.json` lists only
PLA/PETG/ABS/TPU (95A) while the schema enum also has ASA/TPU/PA/PC.

## Goals / Non-Goals

**Goals:**
- Per-union material/color with deterministic slot assignment and a 3MF a slicer opens with
  filaments pre-assigned.
- Planner can propose or accept multiple materials; slot overflow is surfaced to the user.

**Non-Goals:**
- Material boundaries inside a single solid (paint/region splitting).
- Adhesion modeling, purge/waste estimation, soluble-support slicer settings.
- Multi-material FEM (see decision 5).

## Decisions

1. **Resolution** mirrors `units.plate_of`: union `material`, else part, else plan. `color`
   resolves the same way; default color is derived from the material so bodies stay
   distinguishable. Alternative (plan-level map material->color) rejected: two bodies of
   one material may want different colors.
2. **Non-sticky = absence of rules.** No gate, error or warning on contact or overlap
   between different materials. The only consequence is that the planner does not rely
   on adhesion for load, which is prompt guidance, not a check. Alternative (hard joint
   requirement) rejected by the user: PVA support must be allowed to touch.
3. **Slots**: distinct (material, color) pairs, ordered by first appearance, get slots
   1..n. `max_materials` in the profile (default 1 when absent: single-material printer).
   n > max_materials sets a plan-summary warning and the planner asks the user. It does not
   block validation or export, since a manual filament swap is legitimate.
4. **3MF structure (spike result, read from BambuStudio `bbs_3mf.cpp`, master)**:
   - Extruder is an object-level `<metadata key="extruder" value="N"/>` in
     `Metadata/model_settings.config` (the exporter writes `ModelObject::config` keys that
     way); per-volume extruders are the same key inside `<part id= subtype="normal_part">`.
   - Color is read from the 3MF materials extension (`m:colorgroup` / `m:color`, object
     `pid`/`pindex`), NOT `<basematerials>`. The importer numbers extruders by distinct
     color string in order of appearance, so slots that share a color rely on the explicit
     `extruder` key.
   - A multi-volume object is a parent `<object>` with `<components>` of sub-objects, matched
     to `<part id>` entries.
   Shipped (after merging main's `multi-color-3mf-export`): main's writer already emits the
   component layout with per-part `extruder`; this change only supplies the filament, an
   explicit union `filament` else the slot assigned from (material, color). Color is not
   written to the 3MF (the `m:colorgroup` form was dropped in the merge). Not run: an
   OrcaSlicer round-trip (task 1.2).
5. **FEM**: `fem_check` solves one isotropic material. For plans with more than one
   material it skips with a stated reason, as it already does for unknown materials.
6. **Weight**: `quality_gate` runs per part script, so the density is the part's resolved material (part, else plan). Mixed densities between unions of one part are not split. PVA/HIPS have no `material_properties.json` entry and fall back to PLA density.

## Risks / Trade-offs

- Object/volume mismatch makes bodies print apart from each other -> spike first,
  fall back to color-only metadata if the volume form cannot be verified.
- Print orientation picks a pose per union; volumes of one object need one pose ->
  restrict volume grouping to unions already in a shared pose, else separate objects.
- Property table gaps (ASA/PA/PC) -> unknown materials fall back to PLA density as today.
