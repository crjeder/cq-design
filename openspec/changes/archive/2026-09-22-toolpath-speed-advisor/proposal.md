## Why

The skill tells part authors to "fillet a vertical edge -- smooth head motion, fewer
acceleration artifacts" (`src/edge_treatment_check.py`). Nothing measures it, and the
check that exists cannot: `edge_treatment_check.py` hooks `.fillet()` / `.chamfer()`
calls, so it only classifies edges that were *already treated*. It catches "you filleted
the wrong edge" and is structurally blind to "you never touched this 60 mm sharp vertical
edge" -- which is the case that costs print time.

Print time at a fixed slicer profile has exactly one geometric driver: how often and how
hard the toolhead has to slow down. Both halves of that are computable from the part's
own B-rep, with no slicer and no G-code:

- **Corners.** A sharp vertical edge forces the head to a junction-limited crawl once per
  layer, per perimeter, for the edge's entire Z extent. A fillet raises that floor to
  `sqrt(a*R)`. At `a = 5000 mm/s^2` a sharp 90 deg corner allows ~25 mm/s against a
  200 mm/s ceiling; an R2 fillet allows 100 mm/s. The return saturates, so "fillet it"
  is not a binary rule but a knob with a knee, and nothing currently tells an author
  where the knee is.
- **Feature size.** Accelerating 25 -> 200 mm/s takes ~3.9 mm. A part made of 3 mm
  features never reaches cruise anywhere, no matter how well its edges are treated. This
  is the dominant term on detailed parts and the existing guidance has no way to say it.

The same machinery answers a third question the skill currently cannot: whether a pose is
**minimum-layer-time bound**. When a layer's toolpath is shorter than the profile's
minimum layer time, print time collapses to `layers * min_layer_time` and stops depending
on geometry at all -- at which point the only lever is build height, or more copies on the
plate. `print_orientation.py` already enumerates the flat pose as a candidate and already
has a `min_build_height` mode; what it lacks is any reason to pick them.

The prior rejection of slicer integration
(`archive/2026-06-17-trimesh-overhang-analysis/design.md`: *"rejected because it
reintroduces the external dependency ... and is non-deterministic across slicer
versions"*) stands and is not revisited. This change adds no binary, no G-code, and no
dependency.

## What Changes

**New `src/toolpath_speed.py` -- a motion model over the part's own B-rep.** It re-runs
the part script (the execution path `edge_treatment_check.py` already uses), enumerates
**every** edge of the result rather than only treated ones, and builds the mean layer
perimeter directly from the solid: **vertical edges are the path's corners, vertical faces
are the segments between them.** Each edge carries its tangent, turn angle, fillet radius
(0 for a sharp line edge), and Z extent; each face carries its horizontal width. No mesh
sectioning and no triangle-signature guessing -- the B-rep distinguishes a filleted edge
from a bore unambiguously, which is the objection that kept this out of
`edge_treatment_check.py`.

**One formula for every corner.** A corner's sustainable speed is `min(v_cruise,
sqrt(a * R_eff))`, where `R_eff` is the fillet radius for a treated edge and the
junction-deviation equivalent `JD * cos(phi/2) / (1 - cos(phi/2))` for a sharp one
(`phi` = exterior turn angle). The two cases agree at the boundary by construction, so
sharp and filleted edges are ranked on one continuous scale instead of a rule.

**Print time decomposes into three terms that sum exactly.**

```
T_ideal    = L_total / v_cruise                              the floor
T_corners  = sum_i (v_cruise - v_i)^2 / (a * v_cruise)       isolated-corner tax
T_crowding = T_actual - T_ideal - T_corners                  segments too short to cruise
speed_efficiency = T_ideal / T_actual
```

`T_corners` dominating produces *"fillet these edges, ranked, with what each buys"*.
`T_crowding` dominating produces *"your features are too small for the head to ever reach
speed -- consider fewer, larger features"*. One metric, one attribution table, and it
self-suppresses on a part that is already at 90% efficiency. Per-edge attribution is
leave-one-out (`T` recomputed with that edge's `R_eff` set to infinity), so each row
states the time its fillet would actually recover.

**Layer time and stall detection from areas already computed.** Mean layer perimeter is
`A_lateral / H` (exact for a prismatic part, good otherwise), where `A_lateral` is total
surface area minus up- and down-facing area -- the same normal-partitioned sums
`mesh_io.py` already computes per pose for the support score. From that:

```
L_layer = P_mean * perimeters + A_infill * density / line_width
t_layer = L_layer / (speed_efficiency * v_cruise)
stalled = t_layer < min_layer_time
T_total = (H / layer_height) * max(t_layer, min_layer_time)
```

`T_total` is the denominator every corner finding needs to be a percentage of.

**`print_orientation.py` gains `--speed-model <json>` and a `min_print_time` mode.**
Unlike `--fem-stress`'s single authored-frame solve reused across every candidate, the
corner model is not a per-edge property that survives a cheap rotation: which edges form
a layer's cross-section corners depends on which plane is horizontal, so each candidate
re-sections the union's solid after rotating it into that candidate's pose
(`placement.apply_cq`, the same rigid transform `print_orientation.py`'s own candidates
are already expressed in) and re-runs the authored-frame extraction against the rotated
copy. This costs a handful of planar sections per candidate rather than one solve total,
but a section is a fast OCC operation and stays well inside the loop's existing budget.
Layer-time and build-height terms come from the posed mesh directly. Without the flag,
scoring is exactly as today. A new `optimize_for: min_print_time` mode orders on
estimated total time with the existing scores as tiebreakers.

**`printer_profile.json` gains a `motion` block.** None of these constants exist today:
`v_cruise_mm_s`, `accel_mm_s2`, `junction_deviation_mm`, `min_layer_time_s`,
`layer_height_mm`, `line_width_mm`, `infill_density`. They are calibration, not
derivation -- a printer with input shaping runs `a ~ 20000` and every number above shifts
by 2x -- so they are visibly overridable per project, through the existing
`printer_profile_validate.py` write-back path. Absent or partial, the advisor reports a
stated skip rather than assuming.

**The advisor runs in both frames, like the check it extends.**
`edge_treatment_check.py`'s design is already *"apply-time hook + build-frame classify"*;
this follows it. In Phase 3 the findings are conditional and advisory (*"if this edge
ships vertical it costs X"*), giving the author something to act on before an orientation
exists. At the gate stage the same model runs through the accepted orientation and
produces the real numbers. Over-filleting on the Phase 3 hint is cheap; the existing
edge-treatment check already flags a fillet that turns out horizontal, at warning
severity, so the two stages disagree loudly rather than silently.

**Corner findings are never suppressed by a stall.** When a part is minimum-layer-time
bound, filleting recovers no print time -- but a fillet still reduces vibration,
ringing, and machine wear, so the findings stay and only their stated rationale changes
from time saved to motion smoothness. The advisor reports the stall as the reason the time
figure is zero; it does not withdraw the advice.

**Multiplying copies is offered, never taken.** The stall remedy set is: lay the part
flatter (pose), thicken the stalling feature (geometry), or print more copies per plate.
The third changes what the user receives, so the advisor SHALL state it as an option and
SHALL NOT alter plate layout, part count, or `BUILD_PLAN.json` on its own. It is applied
only after explicit user approval, recorded in `request_log` like any other correction.

**Advisory, never a gate.** `toolpath_speed.py` always exits 0, adds no `quality_gate.py`
stage that can fail, and emits the shared issue contract at `severity: "warning"`. A
missing `motion` block, an unparseable script, or geometry the model cannot represent
degrades to a stated skip, also exit 0.

## Capabilities

### New Capabilities
- `toolpath-speed-advisor`: the curvature-limited motion model, the unified `R_eff`
  corner formula, the three-term time decomposition and `speed_efficiency` metric, the
  leave-one-out per-edge attribution, minimum-layer-time stall detection, the slicer-free
  total-time estimate and what it excludes, the two-frame (authored hint / build-frame
  real) contract, the never-suppress-on-stall rule, the copies-require-approval rule, and
  the degradation path when the profile or geometry does not support the model.

### Modified Capabilities
- `print-orientation-optimization`: candidates gain a corner-tax term (from an optional
  `--speed-model` corner model re-extracted per candidate pose) and a layer-time term
  (from the posed mesh); the optimization mode set gains a fifth mode `min_print_time`;
  the emitted
  rationale carries the estimated print time, the speed efficiency, and whether the pose
  is stall-bound. Without `--speed-model`, every existing score and every existing mode is
  byte-identical.
- `printer-profile-config`: the profile MAY carry a `motion` block of machine-motion and
  slicer-profile constants, validated and written back like the existing constraint
  fields; its absence is a stated skip, never an assumed default.

## Impact

- **Code**: `src/toolpath_speed.py` added; `src/mesh_io.py` gains a lateral-area partition
  alongside its existing normal-based sums; `src/print_orientation.py` gains
  `--speed-model`, the two new score terms, and the `min_print_time` mode;
  `src/edge_treatment_check.py` exposes its script-execution path for reuse (no behaviour
  change); `src/printer_profile_schema.json` and `src/printer_profile.default.json` gain
  the `motion` block; `src/printer_profile_validate.py` validates and writes it back;
  `src/quality_gate.py`'s `_emit_print_recipe` carries the estimated time and efficiency.
- **Prompts**: `prompts/part.md` (when to run the advisor, how to read the attribution
  table, that a stall is a pose question and not a fillet question).
- **Skill docs**: `skill/phase3_build.md` (authored-frame hint in the part loop),
  `skill/phase4_deliver.md` (reporting the estimate and its exclusions, and the
  copies-per-plate offer as a user checkpoint), `reference/scripts.md`, `CLAUDE.md`'s
  script index.
- **Reference**: the Chamfer / Fillet guidance in the injected FDM guide gains the
  saturating-return framing and the feature-size term, so the prose and the model agree.
- **Permissions**: `src/skill_permissions.json` gains one allow-pattern pair (Bash +
  PowerShell) for `toolpath_speed.py`.
- **Deps**: none. trimesh, numpy, and CadQuery are all already required.
- **Tests**: `tests/test_toolpath_speed.py` (new -- CadQuery; covers `R_eff` continuity at
  the sharp/filleted boundary, the three-term sum identity, leave-one-out attribution,
  stall detection, and the skip paths), `tests/test_print_orientation.py` gains the
  `--speed-model` and `min_print_time` paths, `tests/test_printer_profile_validate.py`
  gains the `motion` block.
- **No gate behaviour changes.** No stage is added that can fail. A project whose profile
  carries no `motion` block behaves byte-identically to today.

### Non-Goals
- Any slicer, G-code emission, or G-code parsing. The prior rejection stands.
- Absolute print-time accuracy. The estimate excludes travel between islands, solid
  top/bottom layers, seam and retraction time, and per-object heat-up, so it is a labelled
  lower bound for comparing poses, not a figure to set against a real slicer's estimate.
- Modelling arc fitting (G2/G3), pressure advance, or input shaping. Each moves the
  absolute numbers; none change the *ranking* of edges by cost, which is what an advisor
  needs. Their effect is stated, not simulated.
- Automatic geometry edits. The advisor names the edge, the radius, and the recovered
  time; the part author changes the script.
- Automatic plate-layout or part-count changes. Offered to the user, never taken.
- Gating delivery on `speed_efficiency`. Advisory in this change, and a gate is not a
  follow-on promise.
