# Visual Review Checklist

Evaluate the rendered preview PNG of a part against every item below before
marking the part done. Each item is a concrete pass/fail check against the part's
entry in `BUILD_PLAN.json`. If any single item fails, the result is a
`visual_mismatch` (not a pass): name the failed item(s) and use that description
to drive the corrective edit on the next attempt.

The preview tile is a 3x3 grid. Rows 1-2 are the six **exterior** views
(Isometric, Front, Right, Back Isometric, Top, Bottom). Row 3 is the three
**interior cross-sections** (Section Y, Section X, Section Z), each cutting the
part through its bounding-box center. Use the exterior rows for items 1-7 and
the section row for items 8-10.

| # | Check | Pass when | Fails when |
|---|-------|-----------|------------|
| 1 | Shape match | The overall silhouette matches the part `description` and the requested form (box, bracket, cylinder, etc.). | The render shows a fundamentally different shape than described. |
| 2 | Feature completeness | Every feature in `blocks_needed` and every entry in `interfaces` is visibly present (each hole, boss, port, slot, vent, joint). | A planned feature is missing from the render. |
| 3 | Feature placement | Each feature sits on the face and at the position the plan specifies (use the coordinate system: +Y north, +X east, +Z up). | A feature is on the wrong face, mirrored, or rotated from its planned position. |
| 4 | Proportions | Relative extents (W vs D vs H) look consistent with the planned dimensions. | One axis is visibly mis-scaled relative to the others. |
| 5 | Connected geometry | The part renders as a single connected body. | A feature floats free or a body is disconnected/split. |
| 6 | Flat bed face | A flat face sits on the bed at Z = 0 (printable foundation). | The bottom is rounded, pointed, or floating above Z = 0. |
| 7 | Authored orientation | The part rests with the functionally correct face down at Z = 0 -- not just *a* flat face (item 6), but the one that matches the part's own description and features (e.g. a wall-mount bracket's mounting face down, a lid's mating face matching how it meets its counterpart). Final print-bed orientation is chosen separately, later, by the print-orientation optimizer -- this item only checks the authored frame reads correctly. | The part rests on an arbitrary or functionally wrong face -- e.g. upside-down or rotated 90 deg from how its own features imply it should sit -- even though some face is flat at Z = 0. |
| 8 | Hollow / wall integrity | In the section views, hollow regions (cavities, pockets, bores) are actually open and walls have visible thickness where the plan calls for an enclosure. | A part planned hollow renders solid (cut shows filled interior), a wall the plan requires is absent in section, **or a feature added after the cavity (a boss, tab, dovetail, rib) protrudes into the hollow region** — check every feature whose footprint overlaps a cavity's footprint, not just the cavity's own outline; this failure is invisible from every exterior view (see `CadQuery Pattern Reference.md` gotcha 12). |
| 9 | Internal features | Features that live inside the body (blind holes, internal bosses/standoffs, screw bores, captive-nut pockets, internal ribs) appear at the planned depth and position in the section that crosses them. | An internal feature is missing in section, wrong depth (e.g. a blind hole punches through, or a through-hole is blind), or misplaced. |
| 10 | No unintended voids | The section interior is solid where the plan expects solid material. | Section reveals trapped voids, gaps, or non-fused boolean seams that the plan did not call for. |

Notes:
- Judge against the plan and the user's request, not against an idealized version
  of the part. A deliberate design choice recorded in the plan is a pass.
- Numeric concerns (exact wall thickness, exact bounding box, overhang angle) are
  already covered by geometry validation; this checklist is for what only a visual
  inspection can catch (wrong face, mirrored cutout, missing feature, wrong shape).
- For items 8-10, a cross-section that legitimately crosses no interior feature
  (e.g. a solid part with no internal geometry on that plane) is a pass, not a
  miss. Only fault a section when the plan places interior geometry on the plane
  it cuts. If a `WARNING: cross-section ... failed` blank tile appears, treat that
  section as unavailable (skip its items) rather than a fail.
