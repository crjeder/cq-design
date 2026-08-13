# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.

# Feature freeze for V1.0
As of 12.08.2026 only defects will be corrected, no new features introduced.
All completed task are now in `info\DONE.md`

## from C5 Phone-Holder session `session-export-1786538430013.zip` in `./info`:
- [ ] investigate "compass language" `.\info\image-1786538590774.png` shows the problem: east should be right. Reason: mixing up "Viewed from South" and "south facing" under observation
- [ ] the hinge ear shows an old problem: placing primitives with their center aligning to the other parts edge see `.info\image-1786540203166.png`
- [ ] the llm totally did not get that making the knuckle stand of the cradles feet more does not mean that the plate's knuckle has to move upward (+ Z). Probable cause: in the authoring pose the inference is correct, but when the cradle is moved into it's assembled pose it's not a problem.
      Investigated (transcript: session `b6ac548d...`, `session-export-1786538430013.zip`):
      the triggering request was "align the hole with the bore hole on the front plate
      *when the leg lies flat on the front plate*" -- a folded/mounted-pose constraint --
      but `cradle.py` and `plate.py` both hardcode `PIVOT_Y`/`PIVOT_Z` as independent
      literals in the shared car frame (no `joints`/`mate_chain.py` root-derived pose).
      Raising the cradle's own `EAR_STANDOFF` (intra-part, its own resting/authoring
      pose) got mirrored into also raising the plate's `PIVOT_Z` (a separate, stationary
      part whose bore is fixed by its own physical stack) -- treating a shared invariant
      as something to copy-edit in lockstep, which is why PIVOT_Z ping-ponged between
      13.5 and 6.0 across rounds 6/8/9. Two contributing causes, not mutually exclusive:
      (1) hand-duplicated shared pivot constants across sibling part scripts instead of
      going through `joints`/`mate_chain.py`, so nothing forced the second file's copy to
      be *derived* rather than independently re-typed; (2) a conceived resting plane at
      Z=0 (the authoring-pose XY plane) stood in for where the cradle's fold actually
      bottoms out -- in reality the lower stop is below that plane and not flat (console
      floor / hardware clearance), an external constraint neither script models, so
      "the deployed pose sits flat on Z=0" was itself an unverified assumption feeding
      the Z-stack-up math on both sides.

## from Silica Tray `session-export-1786620780455.zip`
- [ ] Silca Tray: LLM claims "no support needed" despite "support score dropped from 654.1" which might be wrong. test needed
- [ ] "I just re-derived the print orientation and re-exported so the deliverables and BUILD_PLAN.json match your hand-edited dimensions: 6mm triangle pitch, 1mm rib width, 20mm total height)." Works, but is it for granted or just coincidence?

- [ ] split `info` directory


# Tasks for next version:

- [ ] ENGINEERING RATIONALE etc. in `BUILD_PLAN.py`? Now it's spread all over the source files.
- [ ] read back parameters on any user initiated planning / authoring round
- [ ] restructure to combat context creep. reference: `ARCHITEKTURE.md` options:
  - [ ] like openspec: phases are own commands, user interaction at the end (change, restart). then start new phase.
  - [ ] python script owns the loop and switches context & models. prompt will be split
  - [ ] use sub-agents / workers for each phase
- [ ] kinematic: explore adding one simple ground/seating plane (lid-hits-floor
      checks); surrounding-geometry questions stay out of scope (external simulation)
- [ ] kinematic: articulated chains (a moving union carries other unions through
      the sweep)
- [ ] joints: multi-DOF / coupled simultaneous movements. A joint is a LIST of
      single-axis movements (`rotate`/`translate`, each with axis + reference
      vector + range); independent movements for now. A spherical/ball joint is
      two coupled `rotate` movements sharing a center -- listing them as two
      independent entries models a 2-axis gimbal, NOT the ball's coupled cone.
      Capture coupling (e.g. helical screw pitch, ball cone) as a later field.
- [ ] export: separate unions into print-plates. Today all unions compile to one
      "world" result and model_export already writes each as a separately named
      3MF `<object>` with `plate` metadata. Core 3MF has no native print-plate
      concept (objects + `<build><item>` only); true multi-plate assignment is a
      slicer-specific extension (Bambu/Prusa project-3MF). Decide: emit the
      slicer plate structure, or leave plate split to the operator.
- [ ] export: automated 2D plate packing / bed nesting. Distinct from the print-plate
      item above (that is about 3MF plate *structure*); this is about *deciding which
      part goes on which plate and where*, which today is declared manually in the plan.
      Prior art: thereprocase/cad-skill Phase 4 -- rasterize each union's XY footprint at
      0.5mm/px (PIL), precompute 0/90/180/270 rotations, bottom-left-fill largest-area-
      first, keep uniform spacing via `scipy.ndimage.binary_dilation` on the blocked
      bitmap, build compound plates with OCC (`BRep_Builder` + `TopoDS_Compound`), export
      STL+STEP per plate, report bed utilization %. Inputs we already have: per-union
      assembled/print-oriented STLs, `plate` metadata, bed size (would need to come from
      `printer_profile.json` -- not currently a field). Decide scope: full nester, or just
      a utilization report + overflow warning leaving assignment to the operator/slicer.
      Interacts with print-orientation (footprint depends on chosen orientation) and the
      plate-clearance check (spacing == the one-layer-height fuse rule). Reimplement
      (PolyForm-safe; algorithm only). Additional prior art: thereprocase/snuggle-demo
      (https://github.com/thereprocase/snuggle-demo) -- a standalone "stuffing"/nesting
      algorithm demo, worth checking against the bottom-left-fill approach above.
- [ ] blocks: assembly placeholder geometry. A block may declare PSEUDO geometry
      marking the volume that must stay clear to ASSEMBLE it (e.g. a hinge's pin-
      insertion path / leaf-swing-during-assembly envelope). It is exempt from
      export (not printed) and from the kinematic sweep (not a moving body), but
      other geometry must not intrude into it or assembly is blocked. Pairs with
      the mating-area footprint (2D where-to-connect) -- this is the 3D keep-clear-
      for-assembly volume. The gate should flag real geometry that violates a
      declared placeholder. Distinct from the model's own clearance gaps.
- [ ] bill of non-printed materials. Surfaced by the `planning_notes` audit's C5
      cross-check (2026-08-12): the plan and the delivery summary have NO field and NO
      section naming anything the user must supply. Verified by grep -- no `BOM`,
      `hardware list`, `required hardware` or `non-printed` anywhere in `src/`,
      `skill/`, `prompts/`, `SKILL.md`, no such key in `build_plan_schema.json`, and
      `skill/phase4_deliver.md` mentions no screw, insert, magnet or assembly step. So
      a user handed an enclosure with `screw_boss`/`pcb_standoff` features is never
      told which screws to buy, and C5's 1.75 mm filament hinge pin survived only as a
      sentence buried in `planning_notes`. Scope: screws/nuts/washers, heat-set
      inserts, magnets, bearings, springs, filament/rod pins, adhesives, and
      quantities. Partly DERIVABLE, which decides the shape: `blocks_needed` hardware
      params (`blocks/hardware.py`'s cq_warehouse fasteners, `screw_boss`,
      `pcb_standoff`) already carry the spec and the count, so the generator can emit
      most rows and only the non-block items (glue, a raw filament pin, a magnet
      pressed into a plain pocket) need declaring by hand. Decide: derived-plus-manual-
      additions (recommended -- keeps the declared surface small) vs. a fully hand-
      authored top-level `bom` array. Output lands in the Phase 4 delivery summary
      regardless. Pairs with the assembly-placeholder item above and with category (c)
      of the `planning_notes` inclusion rule -- (c) records the assembly PROCEDURE, the
      BOM records the PARTS it consumes; if this ships, (c) keeps the procedure and
      hands the hardware list over.
- [ ] joints: side-tagged `face_mount` docks so the planner derives union
      membership and the world joint axis automatically (interface naming: keep
      assembly/mating docks conceptually distinct from kinematic axes even though
      both live in the block `interfaces` array)
- [ ] preview: z-buffered renderer -- matplotlib mplot3d has no z-buffer and
      depth-sorts whole triangles (painter's algorithm), so flat faces show
      cosmetic triangular shading patches where angled wall/fillet triangles paint
      over coplanar ones. Geometry and normals are correct (STL/3MF watertight +
      winding-consistent); the artifact is preview-only. Switching `preview.py` to
      a z-buffered renderer (trimesh + pyrender / `Scene.save_image`) removes it,
      at the cost of an OpenGL dependency that `preview.py`/`mesh_io.py` currently
      avoid by design.
- [ ] preview: render feature detail previews more proactively. The `--detail`
      capability exists (`render_preview.py`/`preview.py` render a high-res zoomed
      view + optional cross-section per named feature; wired in SKILL.md Step 3
      "Feature detail previews"), but in a live run detail previews were not
      generated for small/critical features by default -- only on explicit request
      or the complexity-gate path. Decide when the skill should auto-render a detail
      preview (e.g. every interface/joint feature, or any feature below a size
      threshold vs. the whole-part bbox) so small features are actually inspectable
      without the user asking, and make SKILL.md prescribe it rather than leave it
      to judgement. (Deferred from the orientation/overhang fix session.)
- [ ] anchors: BOSL2-style attachment/anchor helper for INTRA-part feature placement
      (explored 2026-07-22). BOSL2 attachments (BelfrySCAD/BOSL2 wiki
      Tutorial-Attachment-Overview) place children on named parent anchors (TOP,
      RIGHT+FRONT, ...) instead of hand-computed coordinates. Assessment: the
      inter-part half is already covered better by `joints` + block docks +
      `mate_chain.py` (typed anchors, exact composed poses, tree-validated) -- do
      NOT build a parallel assembly language. The gap is intra-part: part scripts
      do coordinate arithmetic by hand (`w_mm/2 - wall - boss_od/2`), which is the
      error class `script_lint` (`magic_number`, `unanchored_feature`), `cq_verify`
      (`check_workplane`, `verify_feature_bounds`) and `feature_presence_check`
      exist to police. Proposed narrow form: a `src/cq_anchor.py` helper importable
      like `cq_verify` (`anchor(body, "TOP+RIGHT", inset=...) -> (x,y,z)` resolved
      from the body/cavity bbox; maybe `place_at(...)` sugar over the boolean) --
      lowers to explicit coordinates at runtime so `feature_presence_check` /
      `import_params` keep working. Plus optionally per-archetype named anchor sets
      in `templates/` (bbox anchors lie on non-box parts like L-brackets/rings).
      Cautions: don't add a 4th positioning concept unless it lowers to the
      existing one; plan `interfaces[].position_mm` stays numeric (symbolic
      positions in the plan schema = much bigger blast radius, separate decision).
      Open questions: (1) quantify via `build/attempts.jsonl` whether placement
      arithmetic is actually the top error class; (2) script-only sugar vs
      plan-level symbolic positions; (3) archetype anchor sets as shared vocabulary
      for visual review. Strategy: reimplement (concept only; BOSL2 is OpenSCAD +
      GPL-incompatible, see Prior-art survey below).
      Concrete failure instance (C5 Phone-Holder session, cradle.py's hinge knuckle,
      see line 12 above): a connecting box's edge coordinate was set equal to a
      circle's CENTER coordinate (reusing the shared pivot variable for both),
      instead of offset by the circle's radius to its tangent line. Booleans still
      succeeded (watertight), so nothing caught it -- only a rendered preview crop
      showed the knuckle as a disc half-buried in a boxy step instead of a
      free-standing round ear on a slim neck. `anchor()`/`place_at()` should make
      "offset to this body's tangent/edge, not its center" the default so this
      class of bug can't be expressed by accident; `script_lint`'s AST-only checks
      can't catch it since it requires tracing which named constant plays which
      geometric role (center vs. edge) across two different primitives.
- [ ] add textures capability https://github.com/Stone-Age-Sculptor/StoneAgeLib/blob/main/images/DemonstrationTexture.png
- [ ] feature: reverse engineer 3D mesh / point cloud into primitives. 
      (-> Differential geometry comparison) / "import" mesh files (.stl) 
- [ ] capability to import (and integrate) B-Rep files (.step. / stp, fcstd, .brep, .iges)
- [ ] form HitsterTower ("D:\Code\cq-design\info\session-export-1786431095406.zip"):
            "Hinges → dovetail corner joints. All 4 pin_hinge kinematic joints are gone. Each corner is now a dovetail_corner_joint (4 pins/tails per corner, 3mm board thickness, 6mm tooth insertion depth, 0.1mm clearance for separable fit). The tower no longer folds — it fully disassembles at all 4 corners into 4 flat panels + base for storage, and presses back together for use. Polarity: every wall carries pins on its east edge, tails on its west edge, so the ring closes consistently (wall_a→wall_c→wall_b→wall_d→wall_a).
            Couldn't express this as a formal top-level joints mate-chain (the schema requires a single-rooted tree; a 4-panel ring produces conflicting/double-anchored paths) — so each wall keeps its own explicit placement, and the dovetail mating is declared through each wall's interfaces instead. Functionally equivalent, just not chained through the schema's joint-tree mechanism."
- [ ] Plan states that parts are pairwise mirrored. LLM generated two files:
      "wall_a vs wall_b: You're right — I over-built. wall_b.py is geometrically identical to wall_a.py (same width, same tenon, same dovetail parameters, both symmetric). I copied it into a separate file out of habit (BUILD_PLAN.json lists 5 distinct part ids), but a symmetric flat panel mirrored is the same printed part — nothing to design twice. I should delete wall_b.py and just have the export use wall_a's STL for both positions (printed twice). Want me to do that now? It also means correcting BUILD_PLAN.json so wall_b references wall_a's geometry instead of carrying its own script."
- [ ] A minimal deliverable for the parametric part. Just the code needed. Not the full `/lib`


## Related ideas
Integration strategy per item avoids the native-vs-MCP false binary. Options, by
how much they preserve upstream updates while staying self-contained and inline
(no MCP):
- **reimplement** -- own code; no upstream updates; on-design.
- **pinned dep** -- declare as a uv git/pip dep, call from a thin `src/` adapter;
  updates via `uv lock --upgrade-package` (same as the existing `cq-warehouse`
  dep); self-contained via the committed lock.
- **vendored snapshot** -- copy source into the repo with license + recorded
  upstream SHA + a documented refresh procedure; manual updates.
- **optional external** -- native by default, use the external tool if present,
  degrade with a warning otherwise (same pattern as `kinematic_check.py` without
  `python-fcl`); off the critical path.

### Gear geometry (lwidm/cq_gears) -- strategy: optional external -- DONE
Parametric involute spur/helical gear generator for CadQuery. Fails the license test
for pinned dep / vendored snapshot: upstream declares no license (`license: null`),
and this project is PolyForm Noncommercial, so bundling isn't safe. No gate check
applies either (nothing is installed or called natively to degrade), so the
integration point is the planning prompt: rule 13 in `prompts/planning.md` tells the
LLM to note in `planning_notes` and point to the repo as a downloadable resource
when a design needs gears, instead of inventing gear geometry from scratch. Also
added to the README Prior-art table.

### Parametric CAD library survey (2026-07) -- strategy varies per item
GitHub survey of reusable OpenSCAD/CadQuery/build123d model libraries, rated for
usability as `src/blocks/` additions. Full ratings table in session history;
summary below. Confirms `cq_warehouse` (already a pinned dep) is the strongest
direct-reuse candidate; everything else is reference-only or needs hand-porting.
- [ ] `cq-gridfinity` (michaelgale/cq-gridfinity, 200 stars, active) -- strategy:
      reimplement (blocks) -- pure CadQuery, narrow domain. Teardrop/bridged-hole
      DFM pattern already tracked above under "Print-friendly parameterizations";
      no separate action beyond that item.
- [ ] `vibe-cading` (fa-mc/vibe-cading, 5 stars, active) -- strategy: reimplement
      (blocks) -- CadQuery + LLM-agent-oriented typed-parameter part classes
      (screws, gears, joints, bearings, heat-set inserts, hinges, standoffs);
      closest philosophical match to this skill's block pattern. Low stars/
      immature -- cherry-pick specific parts as reference when adding new blocks,
      not a dependency.
- [ ] `cadqueryhelper` (medicationforall/cadqueryhelper, 25 stars, active) --
      strategy: reimplement (blocks) -- small CadQuery primitive helpers, borrow
      individual functions if needed.
- BOSL2 (BelfrySCAD/BOSL2, 2252 stars, very active), NopSCADlib (nophead/
  NopSCADlib, 1602 stars), MCAD (openscad/MCAD, 681 stars) -- OpenSCAD, not
  Python; no direct import possible. Reference only for formulas/dimensions
  (threading, gears, standard-part sizes) when a new block needs a formula
  `cq_warehouse` doesn't cover. No action.
- `bd_warehouse` (gumyr/bd_warehouse, 96 stars, active) -- build123d, not
  CadQuery; the actively-maintained successor to `cq_warehouse` with broader
  fastener/thread/gear/pipe coverage. Reference only (hand-port on demand) since
  the kernel wrapper API doesn't match. No action.
- `cqparts` (cqparts/cqparts, 148 stars, unmaintained since 2020) -- wrapper
  framework, assembly abstraction conflicts with this skill's direct-Workplane
  block pattern. Not adopted.
- [ ] `cqMore` and `cqterrain` (`info/Block_Sources.md`, rated High usability) -- no repo
      link or star count recorded in the source survey; re-find and evaluate before deciding
      reimplement vs pinned dep.
- [ ] `partcad/partcad` (`info/related_projects.md`) -- package manager for hardware /
      manufacturable products across CAD kernels (CadQuery, build123d, OpenSCAD). Adoptable:
      package-manager framing for versioned part definitions with declared metadata
      (parallels `blocks/inventory.json`), YAML assembly format tracking BOM/part
      relationships, caching rendered models to speed iteration. Not evaluated for adoption
      strategy yet (reimplement / pinned dep / reference-only).

### Print orientation (Tweaker-3) -- one change -- strategy: reimplement
Clean-room native port of the orientation formulas. Tweaker-3 is GPL-3.0 and this
project is PolyForm Noncommercial; bundling (pinned dep / vendored snapshot) is
license-incompatible, so we reimplement the algorithm (formulas are not
copyrightable) and do NOT copy the GPL code or its verbatim tuned constants --
derive our own. Touches `print_orientation.py` + `mesh_io.overhang_metrics`,
tested via `test_print_orientation.py`.
- [ ] progressive overhang penalty (severity exponent `OV_H`)
- [ ] area-cumulation candidate generation as a fallback/supplement
- [ ] `min_build_height` / volume-minimization mode
- [ ] `FIRST_LAY_H` band for bottom-contact (replaces tight `CONTACT_Z_EPS_MM`)

### CadQuery authoring guidance (jmwright/cadquery-llm-skill) -- one change -- strategy: vendored snapshot
Doc-only; vendoring a doc snapshot is the upstream-recommended usage, so no design
conflict. Record the upstream SHA and refresh periodically. Upgrades `reference/`
and `prompts/part.md`.
- [x] BRep-vs-CSG mindset + selector cheat sheet + anti-patterns + grep-friendly
      local doc snapshot
      Done (change `add-cadquery-anti-patterns`): anti-patterns integrated as
      `reference/CadQuery Anti-Patterns.md` (kernel / stateful-context / API-mechanic
      tiers, always-injected) plus fluent recipes folded into the pattern reference and
      three contradictions reconciled. Free Function API (`cadquery.func`) content
      deliberately excluded -- this pipeline is fluent-only.

### Independent changes
- [ ] OCC deepcopy crash on print-orientation rotation (`info/occ-error.md`): rotating
      certain B-rep solids (seen in `build/plate.py`, an axle bore spanning an open slot,
      or a pure-45-deg pocket ceiling with no flat cap) crashes inside cq_warehouse's
      deepcopy-based `Shape.copy()` -> OCC `BinTools` serialization round-trip
      (`Standard_Failure: BinTools_SurfaceSet::ReadGeometry: UnExpected
      BRep_PointRepresentation = 42`, sometimes flaky). Currently worked around by avoiding
      the triggering geometry shapes (documented in `occ-error.md`), root cause not fixed.
      Leads to investigate: replace cq_warehouse's deepcopy copy with OCC's native
      `BRepBuilderAPI_Copy`; or make `model_export.py` rotate the trimesh (mesh-based) for
      print-oriented 3MF objects instead of the B-rep, sidestepping the deepcopy path
      entirely (the kinematic-check STLs already do this).
- [ ] cadgate-style gate checks -- strategy: optional external (off the critical
      path; gate runs natively, cadgate augments when present). Differential
      geometry (volume/bbox/wall delta vs base) reimplemented in `quality_gate.py`;
      the LLM intent-match is the part that justifies the optional external path
- [ ] `get_parameters`: extract customizable params from a script for parametric
      re-runs (CadQuery/cadquery-contrib mcp-server) -- strategy: reimplement (tiny)
- [ ] DeepCAD evaluation metric: Chamfer distance for golden-mesh regression tests
      -- strategy: reimplement (trimesh already computes it)

### From market research (info/market_research.md)

Recent LLM-CAD / parametric / FDM-printability projects surveyed 2023-2026. The
central finding: LLM-CAD tools stop at "valid geometry" while printability work
(support, orientation, self-supporting design) lives in separate pipelines --
bridging them inline is this skill's clearest opening. Items below are the
reusable primitives, not whole-tool adoptions.

#### Diagnostics-as-assertions (cad-khana, FreeCAD-AI) -- one change -- strategy: reimplement
cad-khana (`github.com/cyberchitta/cad-khana`) is a Claude Code skill / build123d
wrapper that emits a structured `diagnostics.json` (overhangs, wall thickness,
clearances, interferences) and turns geometric constraints into build-failing
assertions (`assert_min_wall`, `assert_clearance`, `assert_no_interference`).
This is the closest analog to our gate; extends `quality_gate.py`.
- [ ] geometric constraints as build-failing assertions feeding the structured
      `{source, severity, type, message, hint}` contract the gate already emits
- [ ] per-project FDM design-rule file (FreeCAD-AI's `AGENTS.md`/`FREECAD_AI.md`
      pattern, e.g. "min wall 1.2mm, all edges >=0.8mm fillet") consumed by the gate

#### Normalized Support Volume score (SEG / ODPO, arXiv 2511.16434) -- one change -- strategy: reimplement
NSV = support-material volume / model volume: a scale-invariant printability cost
(validated against Cura, Pearson r > 0.85 on 50 Thingi10k models). SEG itself is a
diffusion model with no public code; only the *metric* is reusable. Pairs with the
Tweaker-3 print-orientation work above (NSV scores a given orientation).
- [ ] NSV as a quantitative gate score / orientation-selection objective in
      `print_orientation.py` (support volume from the overhang+bed-projection model)

#### Orientation scoring (orient-stl) -- folds into the Tweaker-3 change -- strategy: reimplement
`github.com/sameer/orient-stl` finds best FDM orientation via DIRECT global
optimization (sub-second). Overlaps the existing Tweaker-3 item; the overhang-area +
slice-count fitness from the build-orientation research (genetic-algorithm,
connected-components, "Part Orientation Fused Shape Optimization") is the reusable
scoring function.
- [ ] overhang-area + slice-count fitness as an alternative/cross-check candidate
      score alongside the Tweaker-3 formulas

#### Iterative visual-feedback repair (CADReasoner, CADCodeVerify) -- one change -- strategy: reimplement
CADReasoner (CVPR 2026) and CADCodeVerify (arXiv 2410.05340) close a render ->
diff -> regenerate loop: render the part, auto-generate validation questions,
answer them against the render, feed discrepancies back. We already render
previews (`preview.py`) and run a bounded `claude -p` fix loop in the gate; this
adds the visual-discrepancy signal to that loop.
- [ ] feed multi-view preview renders + auto-generated check questions into the
      gate's correction prompts (currently text-only DFM/geometry findings)

#### Print-friendly parameterizations (cq-gridfinity / Gridfinity practice) -- strategy: reimplement (blocks)
`github.com/michaelgale/cq-gridfinity` and the wider Gridfinity ecosystem encode
concrete DFM heuristics: "lite" thin shells for less material, bridge-over (teardrop)
magnet/screw holes, variable wall thickness. Block-library additions, not a gate change.
- [ ] teardrop / bridged horizontal holes in `blocks/connectors.py` +
      `blocks/fasteners.py` so bosses and ports stay self-supporting

#### Verify-against-criteria tool (CadQuery-MCP `verify_cad_query`) -- strategy: optional external
`github.com/rishigundakaram/cadquery-mcp-server` exposes a `verify_cad_query`
validator that checks geometry against natural-language criteria. The LLM
intent-match overlaps the cadgate item above; same optional-external rationale
(native gate runs without it, augments when present).
- [ ] (covered by the cadgate-style item under Independent changes)

