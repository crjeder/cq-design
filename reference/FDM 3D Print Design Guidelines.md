# FDM 3D Print Design Guidelines

Each `##` section is tagged `<!-- applies_to: ... -->`. Inject a section only if its tag
is `always` or lists a block in the part's `blocks_needed`. Most bullets follow
`Rule: value — why`; some are freeform where a single value doesn't capture the guidance.
Numbers are portable FDM-safe defaults; `planning.md` clearances override where they differ.
Sources: house rules + Rahix, "Design for 3D-Printing" (blog.rahix.de/design-for-3d-printing).

## Baseline & Tolerances
<!-- applies_to: always -->

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
| Interface clearance | press 0.0 / snap 0.15 / sliding 0.25 / loose 0.5 mm | planning.md overrides |
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
<!-- applies_to: always -->

Priority order:
1. Stable base — largest flat face on the bed (wide, low, won't tip).
2. Strong layer bonding — orient to maximize layer-to-layer interface area along the main
   load path so forces don't pull layers apart (see Strength & Load Orientation).
3. Then minimize supports — keep overhangs ≤ 45° from horizontal; lay thin vertical walls
   flat, but recheck that flattening doesn't create a new overhang.

- No orientation satisfies both → split the part. This is a planning decision: revise
  BUILD_PLAN, don't force supports. (Conflicting load directions are also a split reason.)
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

## Strength & Load Orientation
<!-- applies_to: always -->

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

## Make It Adjustable (Tolerance Compensation)
<!-- applies_to: always -->

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

- Min 0.3 mm clearance between surfaces that must stay separate after printing.
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
- Orient text on a VERTICAL face → glyphs print as perimeter lines (max detail).
- Fuzzy skin hides layer lines on vertical faces; improves grip feel on handles.

## Warping Resistance
<!-- applies_to: always -->

- Mostly material-driven; geometry helps: voluminous + smooth rounded surfaces (ideal = sphere).
  Sharp edges and thin sprawling flats warp worst.

## Vase Mode
<!-- applies_to: always -->

- Single-perimeter spiral: fastest, seamless, no stringing, lightweight.
- Add beading (corrugated/ribbed walls) to stiffen otherwise floppy thin shells.
