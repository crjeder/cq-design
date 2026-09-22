# FDM 3D Print Design Guidelines

Each `##` section is tagged `<!-- applies_to: ... -->`. Inject a section into a part
prompt only if its tag is `always` or lists a block in the part's `blocks_needed`; inject
a section into the planner prompt only if its tag includes `planning` (a section may
carry both). Most bullets follow
`Rule: value — why`; some are freeform where a single value doesn't capture the guidance.
Numbers are portable FDM-safe defaults; `planning.md` clearances override where they differ.
Sources: house rules + Rahix, "Design for 3D-Printing" (blog.rahix.de/design-for-3d-printing).

## Baseline & Tolerances
<!-- applies_to: always, planning -->

- Reference printer: 0.4 mm nozzle, 0.2 mm layer height.
- Expectable accuracy: ±0.1 mm per surface. Design for this; never exploit one printer's precision.
- Clearance fit needs > 2x tolerance → ≥ 0.2 mm gap at baseline.

## Basic Dimension Rules
<!-- applies_to: always -->

| Item | Value | Note |
|---|---|---|
| Min wall thickness | ≥ 0.8 mm absolute, design ≥ 1.2 mm | 0.8 = nozzle × 2 (2 perimeters, slicer floor); 1.2 mm (3 perimeters) is the pipeline default the DFM gate checks |
| Fillet radius | ≥ 0.5 mm, default 3 mm | smaller is dropped by slicer |
| Chamfer | ≥ 0.5 mm, default 3 mm | smaller is dropped by slicer |
| Screw hole clearance | +0.4 mm | M3 → ⌀3.4 mm (matches counterbore_hole) |
| Bridge span | ≤ 20 mm | reliable no-support; ~50 mm only with good cooling |
| Overhang angle | ≤ 45° | printable without supports |
| Min hole diameter | ≥ 2.0 mm | smaller holes close up |
| Engraved text | depth 0.4–0.8 mm, stroke ≥ 0.6 mm | portable floor ~0.5 mm depth |

## Wall Thickness
<!-- applies_to: always -->

- Outer walls: 1.2–2.5 mm (default 2.0; 0.8 mm absolute floor); must be a multiple of nozzle diameter.
- Internal ribs: 1.0–1.5 mm.
- Bottom face: ≥ outer wall thickness.
- Strength comes from walls, not infill — add perimeter/wall count before raising infill %.

## Chamfer / Fillet
<!-- applies_to: always -->

| Edge | Use | Why |
|---|---|---|
| Horizontal (∥ bed) | Chamfer | constant overhang angle, clean layer stepping |
| Vertical (⊥ bed `edges("|Z")`) | Fillet | smooth head motion, fewer acceleration artifacts |

- Apply whenever possible to improve part strength and print quality
- Modeling mechanics (fillet sizing limits, fillet-before-shell, cut depth) → CadQuery Pattern Reference "Common Gotchas".
- Combine fillets and chamfers to mitigate overhang issues -> replace a downward face steeper than 45° from horizontal (un-printable) with a chamfer.
- The vertical-edge fillet's speed benefit saturates: raising the radius from sharp to
  roughly 2 mm recovers most of the achievable cornering speed at typical desktop-FDM
  acceleration; radius beyond that buys little more (see `toolpath-speed-advisor`). A
  sharp corner still deserves *some* fillet for smoother head motion even past that
  point — it costs nothing structurally and reduces vibration/wear — just don't expect
  print-time gains from over-sizing it.
- Feature size matters more than any single edge's treatment: a part built from many
  small, closely spaced features never lets the toolhead reach cruise speed between
  them, no matter how well each corner is filleted. Prefer fewer, larger features when
  print speed matters and the design allows it.

## Cosmetic Slopes / Stair-Stepping
<!-- applies_to: always -->

Shallow UP-facing surfaces print as visible layer steps and look bad. This is a cosmetic
concern (up-facing) -- distinct from overhangs (down-facing, a printability failure) and
from edge treatment.

- Avoid up-facing surfaces inclined 5-45° from horizontal on visible faces. Prefer a face
  that is either near-flat (≤ 5°), steep (≥ 45°), or vertical.
- Priority of remedies: (1) don't author the shallow slope -- reshape it to ≥ 45° or
  vertical; (2) let print-orientation rotate it out (automatic in `visual_quality` mode);
  (3) replace it with stacked chamfer steps; (4) lower layer height.
- Layer height only buys smoothness in roughly the 20-45° part of the band; below ~20° the
  steps are wide regardless of layer height, so rotate or reshape instead.
- The gate reports residual up-facing slope area only for `visual_quality` parts (advisory);
  a shallow slope on a hidden structural face is fine. For the down-facing side, see the
  overhang rule and "Chamfer / Fillet" above.

## Screw Mount Structure
<!-- applies_to: screw_boss, pcb_standoff, heat_set_boss -->

- Boss OD: ≥ screw ⌀ × 2.5 (M3 → ⌀7.5 mm+).
- Boss height: = effective screw engagement length.
- Self-tapping pilot hole: screw ⌀ − 0.3 mm.
- Union bosses to body before shelling.

## Snap-fit Design
<!-- applies_to: snap_hook_clip, snap_socket_receiver -->

- Hook thickness: 1.0–1.5 mm.
- Deflection: 0.5–1.0 mm.
- Retention barb: 0.3–0.5 mm.

## Print Orientation
<!-- applies_to: always, planning -->

Priority order:
1. Stable base — largest flat face on the bed (wide, low, won't tip).
2. Strong layer bonding — orient to maximize layer-to-layer interface area along the main
   load path so forces don't pull layers apart (see Strength & Load Orientation).
3. Then minimize supports — keep overhangs ≤ 45° from horizontal; lay thin vertical walls
   flat, but recheck that flattening doesn't create a new overhang.

- No orientation satisfies both → split the part. This is a planning decision: revise
  BUILD_PLAN, don't force supports. (Conflicting load directions are also a split reason.)
- Splitting into printed sub-parts and assembling is often better than one print-in-place
  piece even when a single orientation *would* technically work — each sub-part gets its
  own optimal layer orientation (own strength axis, own stable base), and geometry that
  needs supports as one piece may need none once split. Prefer this over a compromise
  orientation.
- A split line loses strength unless you design alignment into it: add a locating
  dowel/tenon at the joint (positive alignment, resists shear) plus a shallow glue groove
  around it (holds adhesive, resists peel), and drive a pin through perpendicular to the
  joint face for mechanical interlock. Bonded/pinned this way, a split part can match or
  exceed a single print's strength; a plain butt-glued seam won't.
- Mating parts (lid + base): print each show-face-down, opening up — the bed face is
  cleanest. The mating interface is the accuracy-critical surface.

## Holes & Openings
<!-- applies_to: port_cutout, cable_slot, teardrop_bore -->

- Horizontal hole (axis ∥ bed): roof overhangs. Use `teardrop_bore` (`^` peak, self-supporting).
  Small bores (~⌀4 mm) → teardrop point; large bores (~⌀10 mm+) → flat roof 0.4 mm ABOVE the
  true circle so bridge droop lands on-size.
- Vertical hole (axis ∥ Z): best accuracy, but the perimeter seam can shift the wall ~0.4 mm
  and move the centerline; a teardrop keeps the seam off the round wall.
- Large opening: respect bridge span (≤ 20 mm reliable, ~50 mm with good cooling).
- Bottom edge of a hole: chamfer 0.4–1 mm to counteract first-layer squish, which otherwise
  undersizes the hole opening slightly.
- thin, sacrificial bridging can reduce the need for support material.
- stacked triangles in the edges can be used for large sacrificial bridges

## Protrusions & Pegs
<!-- applies_to: teardrop_post -->

Self-supporting horizontal features — pick by function:
- Hole roof overhangs → `teardrop_bore`.
- Free peg/pin/boss underside overhangs → `teardrop_post` (lower half = two 45° faces + flat
  bottom). Use for ⌀ ≥ ~3 mm; below that a plain cylinder self-bridges.
- Peg that must SEAT in a hole → 45°-rotated cube (diamond peg in diamond hole): all faces
  ≤ 45°, both halves print supportless, flats locate positively. (A teardrop_post won't seat
  cleanly in a round socket.)
- Thin vertical pin/rod minimum diameter: ≥ 1.0 mm non-load-bearing, ≥ 2.0 mm if it must carry
  even a light load (a vertical pin's strength is hundreds of weak interlayer bonds stacked up,
  not a single fiber, so it snaps at a layer seam under sideways force). Below that diameter,
  either add a 0.5–1 mm fillet at its base to spread the stress, or tilt it ~30° off vertical so
  it self-supports and prints along a stronger direction instead of stacking straight up.

## Strength & Load Orientation
<!-- applies_to: always, planning -->

- Align tensile/primary loads PARALLEL to the bed (in-plane) — ~3x stronger than across layers.
- **This rule is about tension/bending/shear, not compression.** Those stress the
  interlayer bond, which is the weak direction; a pure compression load (a resting
  weight pressing straight through a base/plinth/pedestal/foot) does not stress that
  bond and doesn't care whether it runs along build Z or in-plane. Don't tip a flat,
  wide, compression-loaded part onto its edge chasing "load in-plane" — that
  optimizes for a failure mode the part doesn't have, at the cost of stability and
  print time. Declare the load as `load.type: "compression"` (see `BUILD_PLAN.json`
  schema / `print_orientation.py --load-type`) so orientation scoring doesn't
  penalize keeping it flat.
- Large cross-sections: thick beats thin; reduce surface area before volume. Square section
  ≥ I-beam in FDM with no time penalty.
- Round transitions and corners — spreads stress, guides loads on short direct paths.
- Complexity is free in FDM — added fillets, ribs, gussets, or an organic transition cost
  no extra print time versus a plain block (time scales with volume/height/perimeter count,
  not shape intricacy). Don't simplify a shape to "save print time"; that's a
  machining-era instinct that doesn't apply here.

## Make It Adjustable (Tolerance Compensation)
<!-- applies_to: always, planning -->

When you can't hit a dimension, design in adjustment:
- Position: oblong/slotted screw holes. Height: opposing screws or spring-opposed grub screws.
  Fine gaps: spring-steel shims.
- Hide error: route seams into sharp concave corners; use shadow lines (recessed lip gap) to
  mask imperfect mating joints.
- **Shadow gap, when a seam between two separately printed parts will be visible on the
  finished piece** (not hidden inside an enclosure): use the `shadow_gap` block
  (`blocks.joints`) rather than hand-rolling a recess. It unions a return-lip onto the
  visible (front) member's inner face; the back member is placed shortened by a
  deliberate ~1 mm reveal and seats against the lip, so the finished seam shows a
  uniform reveal line instead of a raw fit-tolerance gap or color mismatch. Propose it
  by default for any visible multi-part seam during planning (dovetail/finger/
  mortise-tenon docks, abutting panels, quartered or segmented pieces) — don't wait to
  be asked; the user can decline it for a flush look.

## Press Fits & Interference
<!-- applies_to: always -->

- Never circular holes for interference fits (only stretch circumferentially). Use hex/square
  so corners deform elastically.
- Crush ribs (single-assembly): rib −0.2 mm, bore +0.4 mm, tapered entry.
- Grip fins: use instead when the joint is reassembled repeatedly (elastic, not crushing).
- If a round press-fit is unavoidable, cap the interference at 0.15 mm and keep the press-in
  depth shallow — round holes have no corners to deform elastically, so more than that cracks
  the interlayer bond instead of gripping. For a fit that needs real holding strength, prefer a
  looser round hole fixed with epoxy over pushing the interference further.

## Avoiding Support Material
<!-- applies_to: always -->

- First choice: orient to avoid supports. A 45° diagonal tilt often kills long bridges and
  evens out surface finish.
- Sacrificial layer: bridge an internal overhang with one removable layer (drill/cut after).
- Sequential bridging: stack bridges on bridges; each lower one cools before carrying the next.
  Staggered perpendicular bridges support interior geometry ("overhanging counterbore" trick).
- Keep bed-contact area small for easy removal; don't add cutouts to "save material" (extra
  surface area costs more than the volume saves — see Warping Resistance).
- Mouse ears: small flat corner tabs fight bed-lift; trim after.

## Print-in-Place & Flexures
<!-- applies_to: always -->

- Clearance is direction-dependent, not one flat number:
  - Vertical (one part overhangs another): ~0.5 mm for a small overhang (~10 mm); larger or
    more complex overhangs need more — test.
  - Horizontal/XY (sliding fit, e.g. a moving union in a channel): as little as 0.2 mm
    works; stringing is the main risk there, not fusion.
- Flexures: elastic-only deformation; add hard stops so they can't be over-flexed; add a tool
  slot (e.g. screwdriver) to release form-locking clips.
- Living hinges: lie FLAT on the bed (thin sheet flexes across layers); diagonal/bridged hinges fail.
- Break-away tabs support floating geometry in print-in-place mechanisms.

## Threads & Fasteners (Plastic Parts)
<!-- applies_to: screw_boss, pcb_standoff, heat_set_boss -->

| Method | When |
|---|---|
| Tapped/printed thread | low-reuse, quick, no hardware |
| Rib thread forming | single-assembly, no post-processing; taper the entry |
| Heat-set insert | high reuse, robust; NOT back-side (molten plastic blocks bore) |
| Captive nut pocket | side/back-face cutout holds a standard nut |

- Maximize screw length → compression-dominated joint, resists overtightening.
- Dynamic/vibrating loads: threadlocker or lock-nut (plastic preload alone won't hold).
- Embed hardware (magnets, nuts, mesh) mid-print to skip a joining step.
- Zip tie channel: hollow channel / bar to thread the tie around, to lash cables. Orient so
  tie tension loads it in bearing, not shear (shear-loaded thin wall snaps).

## Text & Surface Finish
<!-- applies_to: always -->

- Prefer engraving over embossing (depth/stroke in Basic Dimension Rules).
- If embossing (raised) text is used anyway, size it more generously than engraved text —
  height and stroke ≥ 1.0 mm — since raised strokes blur into layer lines more easily than
  a recessed cut does.
- Orient text on a VERTICAL face → glyphs print as perimeter lines (max detail).
- Fuzzy skin hides layer lines on vertical faces; improves grip feel on handles.
- Flat top surface with an embedded feature (buried nut, sensor, wire) that must look
  unbroken: add a thin cosmetic top layer ~2x layer height (e.g. 0.4 mm over 0.2 mm layers)
  over the feature to bury it and stop nozzle-travel ooze from scratching visible plastic.

## Warping Resistance
<!-- applies_to: always -->

- Mostly material-driven; geometry helps: voluminous + smooth rounded surfaces (ideal = sphere).
  Sharp edges and thin sprawling flats warp worst.
- Large flat panel: prefer a grid of reinforcing ribs on the underside over a thicker solid
  slab — keeps stiffness while cutting the shrinkage-driven warp risk a thick uniform slab has.
  Shallow bed-adhesion grooves (~1 mm wide, ~0.5 mm deep) in a bottom-face grid also increase
  platform grip and resist corner lift on large first layers.

## Vase Mode
<!-- applies_to: always -->

- Single-perimeter spiral: fastest, seamless, no stringing, lightweight.
- Add beading (corrugated/ribbed walls) to stiffen otherwise floppy thin shells.
