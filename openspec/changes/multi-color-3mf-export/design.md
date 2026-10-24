## Context

`deliverables._write_3mf` passes one `(name, plate, shape)` per union to
`threemf_multi.write_named_3mf`, which writes one inline-mesh `<object>` per union plus a
Bambu `Metadata/model_settings.config` holding only `<plate>` entries. Unions that share a
plate are already treated as a rigid cluster: `write_assembly` and the STL plate fuse keep
their assembled relative pose and adopt the first union's print orientation.

The OrcaSlicer and Snapmaker Orca importers (`src/libslic3r/Format/bbs_3mf.cpp`, `main`,
read 2026-10-24) show:

- `model_settings.config` is applied only when `m_is_bbl_3mf` is set. Orca sets it for an
  `Application` starting with `BambuStudio-` or `OrcaSlicer-`; Snapmaker Orca only for
  `BambuStudio-` or `Snapmaker_Orca-`.
- Per-volume settings come from `<object id><part id subtype><metadata key="extruder">`,
  where the part `id` is the component's sub-object id.
- Components carrying `p:path` are resolved against separate model files; that is the
  layout Bambu Studio and Orca write themselves.

## Goals / Non-Goals

**Goals:**
- One slicer object with several bodies, each preassigned to a filament slot, opened
  correctly in OrcaSlicer and Snapmaker Orca.
- Fix Snapmaker Orca ignoring plate assignments.
- Bodies of one object are guaranteed disjoint by the gate.

**Non-Goals:**
- Different materials per body (bonding rules, interlocks): later change.
- Filament colors/presets (`project_settings.config`); the user maps slots in the slicer.
- Triangle painting (`paint_color`), standard `m:colorgroup` colors, preview tinting.
- Checking `filament` against a printer slot count.

## Decisions

**Grouping lives on union entries (`object`, `filament`), not a new top-level section.**
Unions already carry plate, placement and kinematics identity, and a multi-body part is
naturally one script returning a dict. Alternative: a top-level `objects` list referencing
union ids. Rejected: a second namespace to cross-check for no extra expressiveness.

**Members must come from one part and share one plate.** One part means one placement, so
members keep their authored relative pose without extra transforms. One plate means the
existing co-plated rigid-cluster logic already gives them a shared print orientation (the
first member's), so `print_orientation.py` and `write_assembly.py` need no change.
Alternative: allow cross-part groups. Rejected until a real case needs it.

**Bambu layout for grouped objects only.** Grouped objects use root `<components>` plus
`3D/Objects/object_<n>.model` meshes via `p:path` (the user chose the layout Orca itself
writes over inline components, whose handling by the importer is untraced). Ungrouped
unions keep today's inline meshes, so existing behavior and tests are untouched.
Alternative: switch everything to the Bambu layout. Rejected: larger diff, no gain for
single-body objects.

**Generator string `BambuStudio-<version>`.** The only prefix both forks accept. The exact
version token is copied from a 3MF saved by a current Bambu Studio during implementation
(the value is parsed as a Semver and used for preset versioning, not gated on).

**Disjointness is enforced in the plate-clearance stage** using
`interference._intersection_volume` with the same 0.1 mm^3 default tolerance
`kinematic_check.py` uses for `penetration_tol_mm3` (tessellation noise on a shared face). That
stage already iterates co-plated pairs on the same meshes, and object members are always
co-plated. Alternative: check in `run_cadquery_model.py` per part on the BRep. Rejected:
the gate already has the pairwise loop and mesh backend, and this keeps one place that
reasons about union pairs.

## Risks / Trade-offs

- [Bambu generator string makes non-Orca slicers misidentify the file] -> Core 3MF readers
  ignore `Application`; PrusaSlicer does not branch on the Bambu prefix. Accept.
- [Production-extension files unreadable by simple 3MF readers (e.g. trimesh)] ->
  `count_nonmanifold_edges` and tests load via trimesh; verify trimesh resolves `p:path`
  components, else check each `3D/Objects/*.model` mesh directly.
- [Importer details drift between Orca releases] -> A fixture test pins the written
  structure; manual check in both slicers is a task before archiving.
- [Out-of-range `filament`] -> Slicer surfaces it; the user remaps. By decision.

## Resolved Questions

- Generator string: `BambuStudio-01.10.00.00`. OrcaSlicer's Plater treats an untagged
  `BambuStudio-` file at or below 2.3.2 as a compatible older project and, with no project
  config, shows the same geometry-only info it shows for today's `OrcaSlicer-2.3.0`; a
  newer version would route it down the Bambu-project path instead.
- Object-level `extruder`: written as the first member's filament. The importer sets a
  missing object extruder to 1 and, for a single-volume object, erases the volume's own
  extruder, so a lone union with `filament` is written as a one-part component object and
  its slot carried on the object.
- `filament` above the loaded slot count: with no `project_settings.config` the importer
  has no `filament_settings_id` to clamp against, so the value reaches the GUI unchanged.
- Members without an explicit plate default to the `object` id as their plate
  (`units.plate_of`), so a group never splits across plates by default.
