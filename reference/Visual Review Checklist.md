# Visual Review Question Bank

The visual review is **question-driven**, not an open-ended look at one image.
Before reviewing, build a concrete list of yes/no verification questions for the
part under review, then answer each one against a **specific named view** and cite
that view. The review passes only when every question is answered "yes". A single
"no" is a `visual_mismatch` (not a pass): name the failed question and the
discrepancy, and use it to drive the next corrective edit.

This closes the gap that let a part which should have been one body ship as three
detached solids: nothing had forced the reviewer to look at the one section that
crossed the junction. Generating the questions from the plan, and requiring each
answer to cite the view it was judged from, makes that impossible to skip.

## The views you answer against

- **The 2x2 tile** (`<part>_preview.png`): Front (look -Y), Left side (view-from-left,
  drawn top-right), Top (look -Z), and Isometric. The three orthographic panels are
  undistorted; use them for placement, proportion, and bed-face questions. The
  isometric gives the 3D read.
- **Section files** (`<part>_section_*.png`, written by `--cross-sections` /
  `--extra-section` as separate files): interior views cut through the part. Use them
  for connectedness, hollow/wall integrity, and internal-feature questions. Exterior
  panels overlap in projection and can read as connected when they are not, so
  interior questions MUST be answered against a section, never an exterior panel alone.
- **Detail files** (`<part>_detail_*.png`): high-resolution zooms on a small feature.

If no already-rendered view shows the geometry a question is about, render the needed
section (`--extra-section axis=pos`) or detail (`--detail ...`) **before** answering.
An answer you cannot tie to a view that actually shows the geometry is not a pass.

## Universal invariants (always ask these, for every part)

| # | Question | Answer against | Fails when |
|---|----------|----------------|------------|
| U1 | Is the whole part a **single connected body** with no floating or detached solids? | A **section** crossing the body's junctions (not exterior panels). Cross-checked by the deterministic `disconnected_body` wrapper error. | A section shows a gap, or the part is separate pieces that only overlap in exterior projection. |
| U2 | Does a **flat face rest on the bed at Z = 0** (printable foundation)? | Front and Left panels (both show the Z baseline). | The bottom is rounded, pointed, or floating above Z = 0. |
| U3 | Do the **proportions** (W:D:H) match the plan's dimensions? | The three ortho panels + the caption bbox. | One axis is visibly mis-scaled relative to the others. |
| U4 | Does the **overall silhouette** match the part `description` and requested form? | Isometric + ortho panels. | The render shows a fundamentally different shape than described. |
| U5 | Is the **authored orientation** correct -- the functionally correct face down at Z = 0, matching the part's own features (not just *a* flat face)? | Isometric + Front/Left. Print-bed orientation is chosen later by the optimizer; this only checks the authored frame reads correctly. | The part rests on an arbitrary or functionally wrong face (upside-down, rotated 90 deg from how its features imply it should sit). |

## Per-feature questions (generate one per plan entry)

From the part's `BUILD_PLAN.json` entry, generate a question for every declared
element, each answered against the view that shows it (coordinate system: +Y north,
+X east, +Z up):

- **One per `interfaces[]` entry** -- "Is `<type>`/`<connector>` present on the
  `<wall>` face at `<position_mm>`, in the right place and not mirrored?" Answer
  against the panel showing that face, or a section/detail through the position for an
  interior or small feature.
- **One per `blocks_needed[]` entry** -- "Is the `<block>` feature visibly present?"
- **One per declared `union`** -- "Is `<union_id>` a single connected body?" (Answer
  against a section, per U1.)
- **Internal features** (blind holes, captive-nut pockets, internal bosses/ribs,
  screw bores) -- "Does it appear at the planned depth and position?" Answer against a
  section that crosses it; add `--extra-section` at the feature's position if none does.

## Rules

- Judge against the plan and the user's request, not an idealized version. A
  deliberate design choice recorded in the plan is a pass.
- Numeric concerns (exact wall thickness, exact bbox, overhang angle) are covered by
  geometry validation -- this review is for what only inspection catches (wrong face,
  mirrored cutout, missing feature, wrong shape, disconnection visible in section).
- A section that legitimately crosses no interior feature is a pass for that question,
  not a miss. Only fault a section when the plan places geometry on the plane it cuts.
  If a `WARNING: cross-section ... failed` appears, treat that section as unavailable
  (render an alternative position) rather than a fail.
- Every answer cites its view. An uncitable "yes" is not a pass -- render the view.
