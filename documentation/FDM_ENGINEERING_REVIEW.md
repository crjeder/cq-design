# cq-design - FDM / Engineering Review

Reviewer perspective: mechanical engineer + FDM practitioner.
Target user: a person with no 3D-printing or engineering background who wants working
functional parts and assemblies.

Scope read: `SKILL.md`, `skill/phase1..4`, `reference/FDM 3D Print Design Guidelines.md`,
`reference/Engineering Design Rules.md`, `reference/hardware_dims.md`,
`src/profile.default.json`, `src/material_properties.json`, `prompts/planning.md` (fit rules),
`src/quality_gate.py` (print recipe), `src/blocks/inventory.json` (block list).

## Verdict

The geometry pipeline (planning, probes, audit, orientation optimizer, gate) is strong.
The weak spots are the ones a novice cannot compensate for themselves:

1. **No physical feedback loop.** Every fit is a nominal number; nothing calibrates it to
   the user's printer before the real part is printed.
2. **Material and environment are asked, not advised.** A novice will answer "PLA" and
   ship a car-dashboard mount that creeps and sags at 60 C.
3. **No build-volume check.** A part larger than the bed is not detected.
4. **No safety-critical guardrail.** Nothing stops a confident design of a load-over-head
   or child-use part.
5. **Several numeric inconsistencies** between profile, guidelines, and engineering tables
   that make the agents' output depend on which file they happened to read.

## Rating scale

- **Effect**: H = prevents failed prints / failed parts for most novice users; M = noticeable
  quality or reliability gain; L = polish.
- **Effort**: L = prompt/reference edit or < ~50 lines; M = new check or block with tests;
  H = new subsystem or pipeline change.

## Summary matrix

| # | Recommendation | Effect | Effort | Quadrant |
|---|---|---|---|---|
| 1 | Build-volume check + auto-split | H | L | Do first |
| 2 | Fix numeric inconsistencies across references/profile | H | L | Do first |
| 3 | Define `clearance_mm` semantics (per side vs. diametral) | H | L | Do first |
| 4 | Safety-critical application guardrail | H | L | Do first |
| 5 | Environment-driven material advisor (heat, UV, creep, flex, food) | H | L-M | Do first |
| 6 | Load-aware print recipe (walls/infill/brim) | H | L | Do first |
| 7 | Fit-test coupons generated per mating interface | H | M | Plan next |
| 8 | Post-print feedback command that calibrates the profile | H | M | Plan next |
| 9 | Hole-size compensation in profile, applied by bore blocks | M-H | M | Plan next |
| 10 | Load presets for non-mass forces (hand, impact, cable pull) + load-type safety factors | H | M | Plan next |
| 11 | Snap-fit / living-hinge material and orientation checks | M | L | Do first |
| 12 | Elephant-foot chamfer on bed-contact edges of mating faces | M | L-M | Quick win |
| 13 | Pause-at-layer heights for embedded hardware in the recipe | M | L-M | Quick win |
| 14 | Z-height snapping to layer height for critical features | M | M | Plan next |
| 15 | Assembly instructions (`ASSEMBLY.md` + exploded preview) | M-H | M | Plan next |
| 16 | Plain-language checkpoint layer for novices | M-H | L-M | Quick win |
| 17 | Novice default `review_policy` = `checkpoints` | M | L | Quick win |
| 18 | Missing functional blocks (printed threads, gears, bearing seats, magnet pockets, crush ribs) | M | M-H | Backlog |
| 19 | Embed process settings in the delivered 3MF | M | M | Plan next |
| 20 | Conservative interlayer strength values | M | L | Quick win |
| 21 | Shrinkage compensation for ABS/ASA/PA | L-M | L | Backlog |
| 22 | Fast path for trivial single parts | M | H | Backlog |

---

## Do first (high effect, low effort)

### 1. Build-volume check + auto-split

**Finding.** `printer_profile_schema.json` has no bed/build-volume field and no script checks
the print-pose bounding box against the printer (`grep` for build volume / bed size in
`src/`, `prompts/`, `skill/` returns nothing). The Guidelines already say "No orientation
satisfies both -> split the part", but oversize is never detected.

**Recommendation.**
- Add `build_volume_mm: {x, y, z}` to the profile schema and default profile.
- Gate error `exceeds_build_volume` on the print-pose bbox (after `orientations.json`), with
  `action: ask_user`.
- Planner rule: if the envelope from Phase 1 exceeds the bed in every axis-aligned pose,
  plan a split with a dowel + glue-groove joint (the Guidelines already describe this
  joint; `dowel_pin`/`dowel_bore`/`tenon` blocks exist).
- `print_orientation.py`: reject candidate poses that do not fit the bed.

### 2. Fix numeric inconsistencies

The agents receive sections from different files; conflicting numbers make results
nondeterministic. Pick one value and reference it everywhere.

| Topic | Conflict | Suggested resolution |
|---|---|---|
| Bridge span | Guidelines `<= 20 mm`; profile `bridge_max_mm: 10.0` | Keep profile as source; Guidelines say "see `constraints.bridge_max_mm` (default 10)" |
| Dimensional tolerance | Guidelines `+-0.1 mm per surface`; profile `dimension_tolerance_mm: 0.5` | State what 0.5 means (gate tolerance on overall dims?) vs. per-surface accuracy; rename if they are different quantities |
| M3 screw clearance | Guidelines `+0.4 -> 3.4`; counterbore table 3.4; countersink table **3.2** | Use one clearance rule (+0.4 for vertical, +0.5 for horizontal holes) |
| Press fit | Profile `press_fit: 0.0`; Engineering Rules "firm press-fit +0.05 mm **clearance**"; Guidelines "cap round interference at 0.15 mm" | A press fit is negative clearance. Define: round press fit = -0.05..-0.10 (diametral), prefer hex/crush ribs. Fix the table wording |
| Layer anisotropy | Guidelines "in-plane ~3x stronger"; material table PLA 50 vs 30 MPa (1.7x) | See #20; make the prose match the table |
| Print time vs. complexity | "Complexity is free in FDM ... cost no extra print time" vs. the same doc's "many small features never reach cruise speed" and `toolpath_speed.py` | Reword: "fillets/ribs/gussets cost little material; many small, crowded features do cost time" |
| Wall multiple | "must be a multiple of nozzle diameter" | Multiple of **line width** (~0.42-0.45 at 0.4 nozzle); `profile.motion.line_width_mm` already exists |
| Heat-set M3 hole | Table: 4.4 mm for a 4.6 mm OD insert | Common vendor guidance for standard-length M3 inserts is ~4.0-4.2 mm; verify against the vendor datasheet and cite it in the table |
| Default fillet/chamfer | "default 3 mm" | 3 mm consumes a 1.2-2 mm wall; make the default `min(3, 0.5 * local wall)` or 1 mm |
| "Square section >= I-beam" | Not true for bending stiffness per mass | Narrow it: "for small sections, solid beats an I-beam whose web is thinner than 3 perimeters" |

A cheap guard: extend `test_prose_layer.py` (or a new fast test) to assert the numbers that
appear in both the profile and the Guidelines agree.

### 3. Define `clearance_mm` semantics

**Finding.** `prompts/planning.md` rule 4 gives `sliding 0.25`, `loose 0.5` etc. without
saying whether this is per side (radial) or total (diametral). Only `gridfinity.md` says
"per side". A factor-of-2 error on a sliding fit is the difference between "slides" and
"fused" / "rattles".

**Recommendation.** State "per side (radial)" in the schema description, the planning
rule, `fit_clearance_mm` in the profile schema, and every joint block's docstring. Add a
block-level probe/test that a pin in a bore with `clearance_mm = c` has radial gap `c`.

### 4. Safety-critical application guardrail

**Finding.** The target user cannot judge consequence of failure. Nothing in Phase 1
detects applications where a printed part failing injures someone: load over a person
(shelf above bed, ceiling hook, TV mount), climbing/fitness gear, child products, vehicle
or bicycle structural parts, pressurized parts, ladders, pet restraints.

**Recommendation.** Phase 1 prompt rule + oracle statement:
- Classify the application (`safety_critical: bool` in the plan).
- If true: say plainly that FDM layer adhesion makes this unreliable, propose a
  metal/off-the-shelf alternative or a design where the printed part only locates and a
  metal fastener carries the load, and require explicit user confirmation logged in
  `request_log`.
- Use a higher safety factor (see #10) and always run the FEM advisor if available.

### 5. Environment-driven material advisor

**Finding.** Phase 1 asks for "material". A novice does not know the trade-offs; the
material table has PLA, PETG, ABS, TPU only, and no temperature column. Typical novice
failures this would catch:

- PLA in a car, near a window, near electronics, in a dishwasher -> softens (~55-60 C).
- PLA under sustained load (shelf bracket, hanger) -> creeps over weeks.
- PLA/ABS outdoors -> UV embrittlement / yellowing (ASA is the fix).
- PLA living hinge or repeated-use snap -> fatigue cracks.

**Recommendation.**
- Phase 1 asks environment questions instead of "which material": max temperature, indoor
  / outdoor, sustained load yes/no, must it flex, water / food / skin contact.
- Add `max_service_temp_c`, `uv_resistant`, `creep_sustained_factor` to
  `material_properties.json`; add ASA, PA (nylon), PC, and a CF-filled variant.
- Planner picks the material from a small decision table and records the reason in
  `planning_notes`; the gate warns when the chosen material violates a stated
  environment constraint.
- Food contact: warn that FDM layer lines harbor bacteria regardless of filament.

### 6. Load-aware print recipe

**Finding.** `quality_gate.py` print recipe: `walls = ceil(wall_min / nozzle)` (3 at
default), `infill_percent: 20`, `infill_pattern: gyroid` for every part, loaded or not.
The Guidelines themselves say "strength comes from walls, not infill". No brim
recommendation.

**Recommendation.**
- Parts with a plan `load`: 4-6 walls, 30-40 % infill, more top/bottom layers.
- Purely cosmetic / cover parts: keep 2-3 walls, 10-15 %.
- `brim: true` when print-pose height / min base dimension > ~3, base contact area is
  small, or material is ABS/ASA/PA.
- Print the reason next to each setting so the user learns why.

### 11. Snap-fit and living-hinge checks

**Finding.** The snap-fit strain formula is correct, but:
- No rule that the snap arm must flex **in the XY plane** (layers parallel to the arm's
  length). An arm printed upright snaps at a layer line on first use. This is the most
  common functional FDM failure.
- No cycle derating: repeated-use snaps should use ~60 % of the one-time allowable strain.
- No root fillet requirement (>= 0.5 x arm thickness).
- `living_hinge` in PLA/PETG fails quickly; it is a PP/TPU feature (or "fold once" in PETG).

**Recommendation.** Add these to the Snap-fit and Print-in-Place sections, and make the gate
warn when a `snap_hook_clip` arm axis is along print Z or a `living_hinge` is in a rigid
material.

---

## Plan next (high effect, medium effort)

### 7. Fit-test coupons

**Finding.** Phase 1 explicitly says "assumed, adjust after a test fit", and `joints.py`
notes "FDM holes print undersized, so test on a coupon", but no coupon is produced.
A novice prints the full 6 h part, it does not fit, and they do not know which knob to turn.

**Recommendation.** For every mating interface in the plan, `build.py --coupons` emits a
small print (< 10 min) of just the interface (pin + bore slice, snap hook + receiver slice,
lid lip ring segment) at three clearances (nominal, -0.1, +0.1), each labeled by an
engraved number. Deliver it first in Phase 4 with the instruction "print this first; tell
me which number fits best".

### 8. Post-print feedback loop

**Finding.** `fit_clearance_mm` in the profile is the right place for calibrated values,
but nothing writes measured results back except a manual `--set`.

**Recommendation.** A `/cq-design:feedback` command (or Phase 4 follow-up): the user says
"coupon 3 fits", "lid too tight", "hole too small, M3 does not go in", "it broke at the
hook". It maps the symptom to the parameter (`fit_clearance_mm.<type>`, hole compensation,
walls, orientation), writes the profile (`printer_profile_validate.py --set`), logs a
`correction`, and re-runs only the affected parts. Over time the profile becomes a
calibrated model of the user's printer, which is the biggest reliability gain available.

### 9. Hole-size compensation

**Finding.** Vertical holes print undersize (polygon facets + first-layer squish +
seam); horizontal holes print oval. The skill applies a fixed +0.4 screw clearance but no
general compensation, and the Guidelines call vertical holes "best accuracy".

**Recommendation.** Add `hole_compensation_mm` (diametral, default ~0.2) to the profile,
applied by `teardrop_bore`, `dowel_bore`, `counterbore_hole`, etc. Calibrated by #7/#8.

### 10. Load presets and load-type safety factors

**Finding.** `magnitude_n` is only derived from a researched mass with SF 2.0. Most
functional-part failures in novice use come from loads that are not a resting mass: a hand
pushing a button, a cable yanked, a coat dropped onto a hook, a door slamming into a stop,
over-torqued screws. The planner leaves them without `magnitude_n`, so FEM is skipped.

**Recommendation.**
- Presets in `Engineering Design Rules.md`: finger press ~20 N, hand pull ~100-200 N,
  dropped/impact = 3x static, cable tug ~50 N, etc.
- Safety factor by load class: static short-term 2; sustained (creep) 3, or allowable
  x 0.3-0.4 for PLA; dynamic/impact 3-4; safety-critical (#4) 5+ or "do not print".
- Show the load assumption in plain words at the plan checkpoint ("I assumed someone may
  hang up to 5 kg on it").

### 14. Z-height snapping to layer height

**Finding.** In print pose, feature heights that are not a multiple of layer height get
rounded by the slicer: a 0.5 mm floor becomes 0.4 or 0.6, a 0.3 mm snap barb becomes 0.2
or 0.4, a nut pocket depth drifts. No check exists.

**Recommendation.** Gate warning (print pose): critical Z dimensions (interface positions,
thin floors, barbs, nut pocket depths) not within +-0.02 mm of a layer multiple, and any
feature thinner than 2 layers. Or snap them in `print_up`-style finishing.

### 15. Assembly instructions

**Finding.** Phase 4 lists the BOM but gives no assembly order. Novices do not know to
install heat-set inserts before closing a box, which screw goes where, how tight is "tight"
in plastic, or how to break free a print-in-place joint.

**Recommendation.** Generate `ASSEMBLY.md` from the plan (`joints`, `bom`,
`blocks_needed` with hardware) plus an exploded-view preview (`write_assembly.py` already
has assembly pose; offset along each joint axis). Include standard notes per hardware type:
heat-set insert temperature and alignment, "stop when the screw head seats" for
self-tapping, threadlocker for vibrating joints.

### 19. Embed process settings in the delivered 3MF

**Finding.** The print recipe is shown in chat and `README.md`; the novice has to copy
walls, infill, supports, and orientation into the slicer by hand. `estampo_export.py`
already writes some overrides; the default profile format is `step`.

**Recommendation.** Default `preferred_format` to `3mf` for new profiles, write per-object
walls/infill/support/brim into the 3MF's slicer config (Orca/Bambu/Prusa metadata) where
supported, and fall back to the README table elsewhere. Also the default profile ships
`printer: "Snapmaker U1"`; a novice-facing default should be generic or asked in `init`.

---

## Quick wins (medium effect, low effort)

### 12. Elephant-foot chamfer

First-layer squish widens the bottom 0.2-0.4 mm of every part. On a mating face that sits
on the bed, this alone prevents assembly. The Guidelines mention it for hole bottoms only.
Add a print-pose finishing rule (same mechanism as `print_up`): 0.4-0.5 mm 45 deg chamfer on
bed-contact outer edges that belong to an interface or a fit-critical outline.

### 13. Pause-at-layer for embedded hardware

The Guidelines recommend embedding nuts/magnets mid-print, but the recipe does not give
the layer at which to pause. When a pocket is closed over (captive nut, magnet pocket),
compute the print-pose Z of the last layer before the roof and emit
`pause_at_z_mm` / layer number in the recipe and `README.md`.

### 16. Plain-language checkpoint layer

User-facing text uses internal terms: "union", "stub", "probe", "build pose", "interface",
clock positions, compass directions. Compass terms are good for precision but need a
one-time explanation with the concept sketch showing N/E/S/W. Recommendation: one
sentence per checkpoint saying what the user is approving and what a wrong answer costs
("If the hook's opening is on the wrong side, every later step is wasted - please check
this sketch carefully."), and a short glossary the session can link.

### 17. Novice default `review_policy`

Default `every_stage` asks for approval at every stage of every part. For a novice who
cannot evaluate a profile stub, this is approval fatigue that trains them to click
"approve". Use `checkpoints` as default (stages only for parts with interfaces or 3+
blocks) and keep the concept sketch and design approval, which they can evaluate.

### 20. Conservative interlayer strength

`material_properties.json` PLA: `s_z_mpa: 30` vs in-plane 50 (0.6x). Measured FDM Z
strength varies widely (often 0.3-0.6x of XY, worse with cooling fans, fast speeds, and
large layer heights). For a screening tool aimed at novices, use ~0.4x in-plane for Z and
interlayer shear, and state the assumption in the result.

---

## Backlog

### 18. Missing functional blocks

Present: fasteners, snaps, hinges, dovetails, dowels, gridfinity, ball joints.
Not found in `inventory.json`, but common in novice functional requests:

- Printed threads (coarse, >= M8 / jar-lid / bottle-cap profiles with FDM clearance).
- Spur gears and racks (with backlash parameter).
- Bearing seats (608 / 625 press-fit with crush ribs).
- Magnet pockets (with press-fit or pause-embed option, polarity note).
- Crush ribs and grip fins (Guidelines describe them; no block).
- Ribs/gussets as a parametric block honoring the rib:wall <= 0.6 ratio.
- Zip-tie anchor (Guidelines describe it).

### 21. Shrinkage compensation

ABS/ASA (~0.5-0.7 %) and PA shrink enough to matter on fits longer than ~50 mm. Add
`shrink_pct` per material and apply it to fit-critical interface dimensions (or tell the
user to set slicer XY compensation).

### 22. Fast path for trivial single parts

A single-part bracket currently runs research, oracle, planner, builder, auditor,
orientation, FEM, toolpath, gate, assembly, bundle. For a novice this is slow and costly.
When an archetype template matches and there is one part with no mating interface,
consider a reduced route (template + params + gate). High effort because of the pipeline
state machine; listed for completeness.

---

## Suggested order

1. #2, #3 (numbers and semantics; everything else builds on correct values).
2. #1, #4, #5, #6, #11 (prevent the worst novice failures with prompt/profile changes).
3. #7 + #8 + #9 together (coupon -> feedback -> calibrated profile is one feature).
4. #10, #12, #13, #14, #15, #16, #17, #19, #20.
5. Backlog as demand appears.
