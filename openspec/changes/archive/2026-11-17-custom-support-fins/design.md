## Context

cq-design measures overhangs (`mesh_io.overhang_metrics`, `quality_gate`) and scores
orientations (`print_orientation.py`), but has no way to author support geometry. The
[support-fins](https://github.com/gittrahan/support-fins) project (MIT, JavaScript web
app) documents a designed-in fin: a wall standing 0.2 mm off the part, horizontal
one-layer tines that bridge the gap and fuse into the part, a rounded top, an optional
~1 mm bed-pad ellipse. Numbers originate from Slant3D guidance and are unverified here
on a printer. We reimplement from the published spec, not the code.

Constraints: part scripts are authored in build pose; the print pose is only known after
`orientations.json` is accepted ("Three poses" in CLAUDE.md). Multi-union `result` dicts
are already exported/previewed per union. Checks that read the STL (thin regions,
sliver folds, overhang) would misfire on a deliberate 0.2 mm gap.

## Goals / Non-Goals

**Goals:**
- A deterministic, tested CadQuery block that builds one fin from explicit parameters.
- A placement script that suggests fin anchors from the gate's overhang regions.
- Fin geometry travels as its own sacrificial union so existing machinery handles it.
- Gate does not mis-flag the fins; it reports them as designed support.

**Non-Goals:**
- Choosing the orientation, or rotating the part (stays with `print_orientation`).
- Resin pin mode, sway braces, gussets, bed-pad on tilted exports, mesh import UI.
- Automatic insertion into part scripts; the builder places the call.
- Slicer-specific 3MF support settings beyond `enable_support: false`.

## Decisions

1. **Block in `blocks/supports.py`, authored in print-pose-aligned local frame.**
   `breakaway_fin(anchor, down, height, length, layer_h, nozzle_w, ...)` returns a
   Workplane. Placement runs after the orientation is accepted, so the plan stores the
   fin union in *build* pose by inverting `orientations.json` `rotate`. Alternative
   (author in print pose) rejected: breaks the three-poses rule.
2. **Separate union named `support_fins`** with `sacrificial: true` in the plan union
   entry, not boolean-fused into the part. Fusing would defeat the 0.2 mm gap and make
   removal impossible; tines are the only intended contact, and they are part of the fin
   solid that overlaps the part by `tine_overlap`. Alternative (single fused solid)
   rejected: gate checks could not tell fin from part.
3. **`src/fin_placement.py` is advisory JSON, no geometry edits.** Input: print-pose STL
   plus `--overhang-deg`. Output: `{success, errors, fins:[{anchor_xyz_mm, height_mm,
   length_mm, region_area_mm2}]}`. Reuses `mesh_io.overhang_metrics` region grouping
   rather than a second overhang definition (program-vs-prompt rule; no duplicate logic).
   Regions that are bridges (existing `bridges_detected`) and tiny-hole ceilings are
   skipped; Alternative (support-fins' full raster/wedge passes) deferred as over-scope.
4. **Dimensions live in one table** in `reference/support_fins.md` and as module
   constants in `supports.py` (standoff 0.2, tine width 0.4 / height = layer height,
   rounded top, pad 1 mm). Each cites provenance; the block takes layer height and nozzle
   width from `profile.json` so tines stay one bead.
5. **Gate treatment keys off the union flag**, not geometry heuristics: unions with
   `sacrificial: true` are skipped by overhang, sliver_fin, thin-region and per-union
   watertight reporting, and one `designed_support` `info` issue lists fin count and
   total fin volume. Alternative (detect fins geometrically) rejected as fragile.
6. **Estampo export** reads the same flag and writes `enable_support: false` for that
   part (existing per-part key, no new schema field).

7. **Gate hint with plan opt-out.** After an `overhang_exceeded` warning on a union, the
   gate calls `fin_placement.suggest_fins` on the posed mesh and appends a `fin_hint` info
   issue (never blocking; any failure inside the hint is swallowed). The opt-out is
   `constraints.fin_hints` (default true) in `BUILD_PLAN.json`. The plan is the one file the
   gate already reads at the end of the pipeline, so nothing extra is carried; the planner
   writes `false` when the user declines designed-in supports.
8. **Fin block frame.** The block builds in a local frame (wall along X, front face at y=0,
   part face at y=standoff, top at z=height); `place_fin(fin, anchor, outward, up)` maps it
   into the authoring frame. `fin_placement --rotate` supplies `build_*` fields so the
   script needs no pose maths.

## Risks / Trade-offs

- [Dimensions never printed here] -> reference doc and gate `info` text say "unverified";
  cases added to evals before any default-on use.
- [Tines overlapping the part change printed dimensions slightly] -> overlap capped at
  `tine_overlap` (0.2 mm) and recorded in the report.
- [Placement ignores collisions with other geometry] -> fin build checks intersection
  with the part body other than the tine zone and fails with a typed `fin_collision`
  error instead of emitting a bad fin.
- [Orientation changes after fins were authored] -> not detected in v1 (`fins_stale` dropped);
  the `fin_hint` is recomputed on every gate run, so rerunning the gate after a re-orientation
  shows fresh anchors.
- [Union flag adds plan schema surface] -> one optional boolean, defaulting false; old
  plans validate unchanged.

## Open Questions

None. (Resolved: the gate runs the placement as a hint, opt-out via `constraints.fin_hints`.)
