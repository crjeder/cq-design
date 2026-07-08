## Context

The Phase 3 part loop renders a preview and self-reviews it before marking a part
done (`visual-self-review`). Today the render is a nine-up tile (`--cross-sections`
by default) and the review is an open-ended pass over a 10-item checklist
(`reference/Visual Review Checklist.md`). A real failure -- a cradle part that
rendered as three disconnected solids -- slipped through. The disconnection was
visible only in a section that crossed the foot/neck junction, that section lived in
a `--detail` file the review never opened, and the overview it did grade against had
been overwritten. See the proposal for the three compounding causes.

This change is deliberately layered: a deterministic backstop that needs no vision,
plus a question-driven review over a redesigned render so the general case (wrong
feature, missing feature, misplacement) is also forced into view.

## Goals / Non-Goals

**Goals**
- Catch a body that splits into disconnected components deterministically, as a
  blocking wrapper error.
- Replace open-ended visual self-certification with generated per-feature questions,
  each answered against a specific, cited view.
- Guarantee a section view actually crosses each declared feature/union position.
- Redesign the default tile into a legible 2x2 first-angle DIN projection.
- Never review against a stale or overwritten artifact.

**Non-Goals**
- On-image dimension lines. Overall bbox stays in the caption; the reviewer already
  has exact numbers from the JSON `geometry` block. (VLMs misread drawn dimensions.)
- Per-feature dimensioning (hole spacing, diameters). Out of scope; caption carries
  overall extents only.
- A new `src/` question-generator tool. Question generation is driven inline by Claude
  from `BUILD_PLAN.json`, matching the "Claude drives the pipeline inline, there is no
  orchestrate.py" architecture. The only new code is in the wrapper (component count)
  and `preview.py` (layout + section files).
- Changing the wrapper JSON contract keys. `disconnected_body` is a new `errors[].type`
  value, not a new top-level field; `visual_mismatch` remains loop-only, not wrapper-emitted.

## Decisions

### D1: Disconnected-body is a deterministic wrapper check, per union
Each declared union maps to one rigid printed body, so each union's mesh is expected
to be a single connected component. `run_cadquery_model.py` already tessellates and
validates each union body; it additionally splits the body into connected components
(`trimesh.split(only_watertight=False)` / body count) and, when a union yields more
than one, emits `type: "disconnected_body"` with the component count and each
component's bbox + volume, and a hint to union/bridge the pieces. It is blocking
(same class as `non_watertight`).
- Keep-out zones are excluded (never a union body).
- A part may legitimately be one union that is genuinely one body; a multi-union
  `dict` result is still one-body-per-union, so the check is per-union, not per-part.
- Alternative considered: leave connectedness to the visual review only. Rejected --
  it is the exact class of defect that is deterministic and was missed by eye.

### D2: Questions are generated from the plan, answered against cited views
The review derives a concrete question list for the part under review:
- One question per `interfaces[]` entry: "is `<type>`/`<connector>` present on the
  `<wall>` face at `<position_mm>`?"
- One question per `blocks_needed[]` entry: "is the `<block>` feature present?"
- One question per declared `union`: "is `<union_id>` a single connected body?"
- A fixed set of universal invariants that always run: single connected body / no
  floating solids; a flat face rests at Z=0; W:D:H proportions match the plan; overall
  silhouette matches the description; authored orientation is correct.

Each question is tagged with the view that answers it (an ortho panel, the isometric,
or a specific section file). The answer must cite that view. If no rendered view shows
the relevant geometry (e.g. an internal boss with no section through it), the reviewer
renders the needed section/detail before answering -- an uncitable answer is not a
pass. Any "no" is a `visual_mismatch` naming the failed question, feeding the existing
retry budget unchanged.
- This is the CADCodeVerify pattern (render -> generate checks -> answer against the
  render -> feed discrepancies back), scoped to the plan we already have.
- The universal connectedness question is redundant with D1 by design: D1 is the hard
  gate, the question is the human-legible cross-check and covers cases D1 cannot see
  (e.g. two bodies that touch at a point but are functionally separate).

### D3: Default tile is 2x2 first-angle DIN, true orthographic
`render_multi_view` default becomes four panels:

```
+-------------------------+-------------------------+
| Front  (Vorderansicht)  | Left side (Seitenansicht|
| look -Y   [ortho]       | von links) [ortho]      |
| shows W(X), H(Z)        | shows D(Y), H(Z)        |
+-------------------------+-------------------------+
| Top   (Draufsicht)      | Isometric               |
| look -Z   [ortho]       | (pictorial 3D read)     |
| shows W(X), D(Y)        |                         |
+-------------------------+-------------------------+
caption: bbox W x D x H mm | volume | triangles | PLA estimate
```

First-angle placement is honored: Front above Top, Left-side-view drawn on the right.
The three ortho panels set `ax.set_proj_type("ortho")` and exact axis-aligned angles
(no 5-degree tilt), so edges are undistorted. The isometric corner keeps a pictorial
view for depth. Overall bbox stays in the caption; no dimension lines are drawn.
- The old default six-view tile (iso, front, right, back-iso, top, bottom) is
  replaced. Bottom and back-iso drop from the default; the flat-bed-face check (item 6)
  is preserved because Front and Left-side both show the Z=0 baseline as the bottom edge.
- Alternative considered: keep 3x2 and just add ortho. Rejected -- fewer, larger,
  purpose-labeled panels are the point (contact sheets degrade VLM attention).

### D4: Cross-sections become separate files, on request, through declared positions
`--cross-sections` no longer appends a section row to the tile. It writes one section
file per cut, cut through each declared feature/union position from the plan (falling
back to bbox-center when no positions are declared), named per the existing
`--detail`/section convention. The review opens these files and answers the interior
questions (connectedness at a junction, internal feature depth) against them, one at a
time.
- This is what gives the connectedness/internal questions a view that actually crosses
  the geometry -- the coverage failure from the post-mortem.
- Alternative considered: keep sections in the tile. Rejected -- a section crammed into
  a corner tile is what was ignored; a separate file the review must open and cite is
  the forcing function.

### D5: Review artifacts are not overwritten before they are read
The files a review depends on (the tile and its section files for the part/attempt
under review) SHALL persist until the review has read them. The renderer writes to
stable per-part names and the loop reads them within the same attempt before any
re-render can clobber them. This directly fixes the "overview overwritten, not
available" cause.

## Risks / Trade-offs

- [Losing Bottom / Back-Iso from the default tile] -> Flat-bed-face and rear-feature
  checks move to the Front/Left-side ortho panels (both show the Z baseline) and the
  isometric; a rear-only feature gets a targeted section or detail like any interior
  feature. Net legibility gain outweighs the two dropped exterior angles.
- [Question generation is inline, not a tested script] -> Matches the existing
  architecture; the deterministic backstop (D1) is the tested, load-bearing catch.
  The questions add a forcing function, not a correctness guarantee.
- [`disconnected_body` false positives] -> Only fires when a union's mesh is genuinely
  multiple components; a single fused body is one component. Point/edge-touching bodies
  that OCC fuses into one shell read as connected (correctly). Truly separate declared
  unions are checked independently, so a multi-body part is not flagged.
- [`--cross-sections` semantic change is breaking for callers] -> Only internal callers
  (`SKILL.md`, the wrapper) use it; both are updated in this change. No archived output
  depends on the old in-tile section row.

## Migration Plan

1. Add the per-union component-count check + `disconnected_body` error to
   `run_cadquery_model.py`; test in `test_run_wrapper.py` (a two-box non-overlapping
   union result asserts one `disconnected_body` error).
2. Redesign `render_multi_view` to the 2x2 first-angle ortho layout; update
   `test_preview.py`. Keep `render_single` and the detail/section renderers.
3. Change `--cross-sections` to emit separate section files through declared positions
   in `render_preview.py` + `run_cadquery_model.py`.
4. Rewrite `reference/Visual Review Checklist.md` as a question bank (universal
   invariants + per-feature template) and `SKILL.md` Step 3/4 to the question-driven
   flow with cited views and artifact persistence.
5. Run `test_run_wrapper.py`, `test_preview.py`, and `openspec validate
   verification-driven-review --strict`.

Rollback: revert; the nine-up tile, in-tile sections, and open-ended checklist return.
No stored data depends on the new behavior.

## Open Questions

None blocking. Later (not in scope): per-feature dimensioning; auto-deriving section
positions for features whose position is implicit rather than declared in `interfaces`.
