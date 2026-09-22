# Design: toolpath-speed-advisor

## Context

The skill is deliberately slicer-free, and that decision is documented and still holds
(`archive/2026-06-17-trimesh-overhang-analysis/design.md`). The question this change
answers is whether print speed can be advised on *without* reversing it. It can, because
at a fixed slicer profile the only geometric input to print time is how often and how hard
the toolhead decelerates, and that is a property of the part's own curvature -- readable
straight off the B-rep.

Constraints: no new dependency (CadQuery, trimesh, numpy only); advisory, never a gate;
Python 3.10-3.12; per-candidate cost must stay negligible so `print_orientation.py`'s
existing loop is unaffected.

**Goals**
- Turn the prose rule "fillet vertical edges" into a measured, ranked, saturating number.
- Say the thing the prose rule cannot: that a part's features are too small to ever reach
  cruise, which on detailed parts dominates every fillet.
- Detect minimum-layer-time stalls, where geometry stops mattering and only height does.
- Give `print_orientation.py` a print-time objective, since it already enumerates the
  poses that would fix a stall and has no reason to choose them.

**Non-Goals**
- Any slicer, G-code emission, or G-code parsing.
- Absolute time accuracy competitive with a real slicer's estimate.
- Automatic geometry, plate-layout, or part-count edits.

## Decisions

**Decision: an exact CAD-solid section, not a mesh section and not per-edge enumeration.**
`edge_treatment_check.py` states the reason mesh-based classification was avoided before:
*"a filleted edge and a legitimately-round bore share the same triangle signature."* The
original draft of this decision proposed instead walking the solid's own vertical edges
and vertical faces (no sectioning at all), reasoning that a fillet's own edges would be
vertical arcs running the height of the corner. Building the extractor disproved that:
CadQuery represents a filleted vertical corner as two vertical *straight* tangent-line
edges (where the round surface meets the two adjacent flat faces) plus *horizontal*
circular arcs only at the top and bottom rims -- there is no vertical arc edge to read a
radius from, so the original per-edge plan cannot recover per-corner radius at all.

What works, verified directly against CadQuery's `Workplane.section`, is sectioning the
*exact CAD solid* (not its tessellated mesh) at a representative height: the returned
face's `outerWire()` gives the true cross-section boundary as `LINE` (wall) and `CIRCLE`
(fillet, with exact `edge.radius()` and exact sweep-angle arc length) edges, in order,
and a bore or pocket appears as a separate *inner* wire -- excluded by construction,
never by shape-guessing. This keeps the "B-rep, not mesh" property the original decision
wanted (the section is an exact OCC operation on the solid, not a triangle count on its
tessellation) while actually working. Verified empirically: a box with `edges("|Z")
.fillet(3)`, sectioned mid-height, returns exactly 4 `LINE` walls of length 14 (20 - 2*3)
and 4 `CIRCLE` corners of radius 3.0, arc length 4.712 (a quarter circle); the same box
with a `.hole(4)` bore instead returns the bore as a separate inner wire, absent from the
outer-wire walk entirely.

Alternative considered: `trimesh.section` on the tessellated mesh, integrating the real
2D path. Rejected as tier-2 -- it reintroduces exactly the triangle-signature ambiguity
this decision exists to avoid, needs its own layer-band bookkeeping, and buys accuracy
this advisor cannot use. Revisit only if the section model's ranking is shown to disagree
with a real slice.

**Decision: the sectioned outer wire IS the mean layer perimeter, at a representative slice.**
For a prismatic solid, every layer's cross-section is identical, so one section at a
mid-height gives the corner/wall model exactly. For a non-prismatic part, `_N_SLICES`
representative heights are each sectioned independently and the *modal* (most common)
corner-count result is taken as representative -- robust to one or two slices landing on
a taper, chamfer, or step that the rest of the height does not share. The fraction of
slices that produced a usable section is reported as `height_coverage`; see the Risks
section for what falls below the floor.

**Decision: one corner formula, via an effective radius.**
Firmware junction deviation and a real fillet are usually treated as separate cases. They
are the same case. Marlin's junction limit, with `phi` the exterior turn angle
(`0` = straight, `pi` = reversal, so `dot(prev_dir, curr_dir) = cos phi`):

```
v_j^2 = JD * a * sin_half / (1 - sin_half),   sin_half = sqrt(0.5 * (1 + cos phi)) = cos(phi/2)
```

which is algebraically `v_j = sqrt(a * R_eff)` with

```
R_eff = JD * cos(phi/2) / (1 - cos(phi/2))
```

So a sharp corner already *is* an arc of radius `R_eff`, and a filleted one is an arc of
radius `R`. Both go through `v_corner = min(v_cruise, sqrt(a * R_eff))`. Checks:
`phi -> 0` gives `R_eff -> inf` (straight, no limit); `phi = pi/2`, `JD = 0.05` gives
`R_eff = 0.121 mm` and `v_j = 24.6 mm/s` at `a = 5000`; `phi -> pi` gives `R_eff -> 0`,
`v_j -> 0` (full reversal). This is the single most useful thing in the change: it makes
"sharp" and "R0.5" and "R5" points on one continuous axis instead of a rule with
exceptions, which is what lets the advisor report a *knee* rather than a verdict.

**Decision: three terms that sum exactly, not a bag of findings.**
A per-edge threshold lint would fire on nearly every part (a 4 mm wall already fails to
reach cruise), which is threshold spam, not advice. Instead, one scalar with an exact
decomposition:

```
T_ideal    = L_total / v_cruise
T_corners  = sum_i (v_cruise - v_i)^2 / (a * v_cruise)     each corner as if isolated
T_crowding = T_actual - T_ideal - T_corners
speed_efficiency = T_ideal / T_actual
```

`T_corners` uses the closed form for a full decelerate-and-reaccelerate around one corner
on an infinitely long segment. `T_actual` is the real trapezoid traversal of the closed
path, where a segment shorter than `2 * d_accel` never reaches `v_cruise`. The residual is
therefore exactly the cost of corners being *close together*, which is the feature-size
term -- and it is non-negative by construction, since no finite segment can beat the
infinite-segment case. Two dominant-term cases, two different sentences:

```
   T_corners dominant  -> "fillet these edges" + ranked table + what each buys
   T_crowding dominant -> "features too small to reach speed; fewer, larger features"
```

Alternative considered: emit one finding per bad edge with a severity threshold. Rejected
-- no threshold separates "sharp edge on a chunky part, irrelevant" from "sharp edge on a
small part, dominant," because the answer depends on the whole path, not the edge.

**Decision: per-edge attribution is leave-one-out.**
Row value = `T_actual` recomputed with that edge's `R_eff` set to infinity, minus
`T_actual`. This answers exactly the question an author asks ("what does filleting *this*
buy?") and is well-defined even where corners interact. It does not sum to `T_corners`
when corners are crowded -- stated in the output, not hidden, because the gap is itself
the signal that the part is crowding-bound and fillets are the wrong lever.

**Decision: layer perimeter from lateral area, not from sectioning.**

```
A_lateral = A_total - A_up_facing - A_down_facing
P_mean    = A_lateral / H
```

Exact for a prismatic part. Verified on a 30x30x60 box with 2 mm walls:
`A_lateral = 4*30*60 + 4*26*58 = 13,232 mm^2`, `H = 60`, `P_mean = 220.5 mm` against a
true cross-section perimeter of `4*30 + 4*26 = 224 mm` -- 1.6% low, and the error is the
top/bottom rim area, which shrinks as parts get taller (exactly where stall detection
matters). `mesh_io.py` already partitions faces by normal for `bed_contact_mask`,
`up_facing_incline_area`, and `support_cost`, so this is one more sum over the same
arrays, per pose, for free.

**Decision: stall detection needs an infill term or it over-fires.**
Perimeter alone under-predicts layer path on a solid part, which would report a stall that
will not happen. Cross-section area is free (`V / H`), so:

```
A_band    = P_mean * perimeters * line_width        area the perimeters themselves cover
A_infill  = max(0, V / H - A_band)
L_layer   = P_mean * perimeters + A_infill * infill_density / line_width
```

Box check (`perimeters = 5` from `ceil(2.0 / 0.42)`, `line_width = 0.42`,
`infill_density = 0.15`): `A_band = 463 mm^2`, `V/H = 269 mm^2`, so `A_infill = 0` --
correctly recognising a thin-walled box as all-perimeter, no double count. A solid 20 mm
cube at the same settings gets `A_band = 168`, `V/H = 400`, `A_infill = 232`, adding
83 mm of infill path -- correctly un-stalling it. `perimeters` comes from the same
`max(2, ceil(wall_min / nozzle))` `_emit_print_recipe` already computes, so the recipe and
the model cannot disagree.

**Decision: re-section per candidate pose, via `placement.apply_cq`, not a tangent rotation.**
`--fem-stress`'s "one solve, N orientations" was the original template for this, on the
assumption that a per-candidate quantity could be recovered by rotating a fixed
authored-frame tangent table -- the same pattern `edge_treatment_check._classify` uses to
reclassify a recorded tangent into the build frame via `placement.transform_direction`.
That pattern only works because edge-treatment classification is a per-edge property
(is *this* edge's build-frame tangent horizontal or vertical) that survives rotation
unchanged and just needs re-testing. The section-slice corner model is not a per-edge
property: *which* edges even appear as corners in a layer's cross-section is decided by
which plane is horizontal, and rotating a solid changes which of its edges lie in any
given horizontal slice. A radius is rotation-invariant, but the *set* of corners a pose
exposes is not, so there is nothing to usefully rotate.

What is cheap instead is repeating the extraction itself: `placement.apply_cq(workplane,
{"rotate": candidate["rotate"]})` returns the union's solids rigidly transformed into
that candidate's build frame (already the mechanism `print_orientation.py`'s own
candidate poses are expressed in), and `extract_corner_model` runs unchanged against the
rotated copy, sectioning along its own new Z. Per-candidate cost is the same handful of
planar sections as the authored-frame extraction -- not free like a tangent rotation, but
section is a fast OCC operation and the existing candidate counts (tens per union) keep
this well inside the loop's existing budget.

**Decision: `min_print_time` is a mode, not a new default.**
`optimize_for` gains a fifth value ordering on `T_total` with the existing scores as
tiebreakers, on the same tolerance-band pattern the other four modes use. Default stays
`strength`. Making speed the default would silently trade strength for time on every
existing project.

**Decision: `motion` is a new top-level profile block, not more `constraints` keys.**
`constraints` holds DFM limits a part must satisfy; `motion` holds machine and slicer
profile constants that describe how the printer *moves*. Different kind, different block,
even though `constraints` is `additionalProperties: true` and would have accepted them.
Every value is calibration: a printer with input shaping runs `accel_mm_s2 ~ 20000` and
halves every corner tax in this document. There is no defensible derived default, so an
absent or partial block is a stated skip and never an assumption.

**Decision: fillet findings survive a stall.**
When `t_layer < min_layer_time`, `T_total = layers * min_layer_time` and no fillet changes
it. Suppressing the corner table there would be wrong: a fillet still reduces vibration,
ringing, and machine wear. The findings stay; their rationale field switches from time
recovered to motion smoothness, and the stall is reported as the reason the time column
reads zero.

**Decision: more copies per plate is offered, never taken.**
It is the most effective stall fix -- N copies multiply `L_layer` by N at no per-part time
cost -- and it changes what the user physically receives, so it is a user decision. The
advisor states it as an option alongside re-posing and thickening; it never edits plate
layout, part count, or `BUILD_PLAN.json`. Approval is recorded in `request_log` like any
other correction, so the change is traceable to the user who asked for it.

## Worked Numbers

At `v_cruise = 200 mm/s`, `a = 5000 mm/s^2`, `JD = 0.05 mm`:

```
  treatment        R_eff     v_corner    isolated tax (v_c-v)^2/(a*v_c)
  -----------------------------------------------------------------
  sharp 90 deg     0.121     24.6         30.6 ms
  fillet R0.5      0.5       50.0         22.5 ms
  fillet R2        2.0      100.0         10.0 ms
  fillet R5        5.0      158.1          3.5 ms
  straight         inf      200.0          0
```

The knee is near R2: R0 -> R2 buys 20.6 ms/corner, R2 -> R5 buys 6.5 more. Segment length
at which cruise is reached from a sharp corner: `d_accel = (200^2 - 24.6^2) / (2*5000)
= 3.94 mm`, so a face narrower than ~7.9 mm never cruises.

Stall example, 30x30x60 box, 2 mm walls, `layer_height = 0.2`, `min_layer_time = 5 s`,
`speed_efficiency = 0.6` so `v_mean = 120 mm/s`: `L_layer = 220.5 * 5 = 1102 mm`,
`t_layer = 9.2 s > 5 s` -- not stalled, `T_total = 300 * 9.2 = 46 min`. Shrink the
footprint to 12x12 and `L_layer = 199 mm`, `t_layer = 1.7 s < 5 s` -- stalled,
`T_total = 300 * 5 = 25 min`, and no fillet changes it.

## Risks / Trade-offs

- [The mean-layer-perimeter model assumes prismatic geometry] -> Each edge contributes
  weighted by `z_extent / H` and each face by its Z-overlap fraction, collapsing the part
  to one representative layer. A part whose cross-section changes substantially with Z
  (a cone, a stepped boss tower) is modelled poorly. Mitigation: report the weighted
  fraction of the height the model actually covers, and skip with a stated reason below a
  floor. Upgrade path is Z-banding -- the same computation over a handful of height bands
  -- carried as a `ponytail:` comment naming the ceiling, not built speculatively.
- [Absolute time is optimistic] -> Excludes travel between islands, solid top/bottom
  layers, seam and retraction time, and per-object heat-up. Labelled a lower bound in the
  output field name and in the delivered recipe, and never presented as comparable to a
  slicer's estimate.
- [Arc fitting, pressure advance, and input shaping all move the numbers] -> Each scales
  the tax roughly uniformly across corners, so the *ranking* of edges and the
  corners-vs-crowding verdict hold even where the seconds do not. The advisor's output is
  ranked and proportional for exactly this reason; `accel_mm_s2` is the knob a user turns
  when their printer's real behaviour differs.
- [Running the part script a second time costs build loop time] -> It is the path
  `edge_treatment_check.py` already takes at the same stage, so the marginal cost is one
  more script execution in a phase that already runs several. If it proves material, the
  two checks share one execution.
- [Phase 3 authored-frame hints can suggest a fillet on an edge that ships horizontal] ->
  The hint states its assumption, and the existing edge-treatment check flags a fillet on
  a horizontal edge at warning severity, so a wrong hint is caught downstream rather than
  silently shipped.

## Migration Plan

1. `mesh_io.py` lateral-area partition + tests (pure addition, no caller changes).
2. `printer_profile_schema.json` / `.default.json` / `printer_profile_validate.py` gain
   `motion`; absent block behaves as today.
3. `toolpath_speed.py` with the corner model, the three-term decomposition, and the
   authored-frame report; tests cover the `R_eff` boundary continuity and the sum identity.
4. `print_orientation.py` gains `--speed-model`, the two score terms, and
   `min_print_time`; without the flag every existing test passes unchanged.
5. Gate-stage wiring, `_emit_print_recipe` fields, prompt and skill-doc updates.

No data migration. Rollback is reverting the commit; a profile carrying an unused `motion`
block is inert.

## Open Questions

- **Does the B-rep path model agree with a real slice?** Not blocking (the advisor is
  advisory and the ranking is the product), but worth one manual spot-check against a
  slicer on two or three eval cases before the numbers are quoted in `print_recipe`.
  Disagreement on *ranking* -- not on absolute seconds -- would be the signal to
  reconsider tier-2 sectioning.
- **Should `speed_efficiency` have a reporting floor?** Emitting the table at 92%
  efficiency is noise. A floor is obvious; where it sits is not, and it should be picked
  from the eval corpus's actual distribution rather than guessed.
- **Is `min_print_time` distinct enough from `min_build_height`?** On stalled parts they
  select identically by construction. They diverge only on non-stalled parts, where time
  is curvature-driven and height is not. If the eval corpus shows they never diverge in
  practice, `min_print_time` should be dropped and the time estimate kept as a reported
  number only.
