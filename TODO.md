# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.


- [ ] optimize prompts, they are growing to long
  - [x] Pass 1 done: `emboss_text.md` (text/emboss gotchas) is now appended to
      `{{CQ_REFERENCE}}` only for parts that involve text (was concatenated into every
      part prompt); removed the duplicate fit-clearance row from the FDM "Basic Dimension
      Rules" table (planning.md rule 4 is the source of truth); verified the coordinate
      tables in planning.md/part.md/SKILL.md are consistent.
  - [ ]  the planning.md template itself (13 verbose rules) could be condensed.
- [ ] restructure to combat context creep. options:
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
      (PolyForm-safe; algorithm only).
- [ ] blocks: assembly placeholder geometry. A block may declare PSEUDO geometry
      marking the volume that must stay clear to ASSEMBLE it (e.g. a hinge's pin-
      insertion path / leaf-swing-during-assembly envelope). It is exempt from
      export (not printed) and from the kinematic sweep (not a moving body), but
      other geometry must not intrude into it or assembly is blocked. Pairs with
      the mating-area footprint (2D where-to-connect) -- this is the 3D keep-clear-
      for-assembly volume. The gate should flag real geometry that violates a
      declared placeholder. Distinct from the model's own clearance gaps.
- [ ] joints: side-tagged `face_mount` docks so the planner derives union
      membership and the world joint axis automatically (interface naming: keep
      assembly/mating docks conceptually distinct from kinematic axes even though
      both live in the block `interfaces` array)
- [x] `interface` third type: `union` (fused into the parent part's body, distinct from
      mating docks like `face_mount` and kinematic axes like `hinge_axis`) -- DONE.
- [x] `hinge_axis` interface type is too narrow: generalize the kinematic-axis vocabulary
      (revolute/prismatic/spherical) rather than the single `hinge_axis` token -- DONE
      (replaced by motion-agnostic `joint_axis`).
- [ ] preview: z-buffered renderer -- matplotlib mplot3d has no z-buffer and
      depth-sorts whole triangles (painter's algorithm), so flat faces show
      cosmetic triangular shading patches where angled wall/fillet triangles paint
      over coplanar ones. Geometry and normals are correct (STL/3MF watertight +
      winding-consistent); the artifact is preview-only. Switching `preview.py` to
      a z-buffered renderer (trimesh + pyrender / `Scene.save_image`) removes it,
      at the cost of an OpenGL dependency that `preview.py`/`mesh_io.py` currently
      avoid by design.
- [x] preview: cross-section previews wired into workflow. The `--cross-sections`
      flag now renders a 3x3 grid (6 exterior + 3 interior section views) as the
      default for whole-part validation. Visual Review Checklist extended with
      items 8-10 (hollow/wall integrity, internal features, unintended voids) to
      exploit the interior views. (DONE: PR #39).
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
- [x] gate: enforce `reference/FDM 3D Print Design Guidelines.md`'s "Chamfer /
      Fillet" rule (horizontal edges -> chamfer, vertical edges -> fillet). Done via
      `src/edge_treatment_check.py`: instead of classifying edge treatment from a
      triangulated mesh (a filleted edge and a round bore share the same triangle
      signature), it inspects the treatment at apply-time -- wraps `cq.Workplane.fillet`/
      `.chamfer`, re-runs the part script to record the exact BRep direction of every
      treated edge (round features never pass through a fillet/chamfer call, so no false
      positives), then classifies each in the build frame (authored-frame tangents rotated
      through the union's print orientation via `placement.transform_direction`). A fillet
      on a horizontal edge and a chamfer on a vertical edge are advisory (`warning`)
      findings; diagonal edges and tilted rims are passed silently. Wired into
      `quality_gate.py` as a once-outside-the-fix-loop stage.
- [x] gate + guide: small up-facing slopes stair-step and look bad (COSMETIC only).
      DONE via openspec change `cosmetic-slope-gate`: scoped in an explore session to the
      cosmetic stair-stepping of UP-facing surfaces inclined ~5-45 deg from horizontal (NOT
      overhang, NOT edge treatment). Shipped `mesh_io.up_facing_incline_area` +
      a `cosmetic_slope_area_mm2` field on the print-orientation result, surfaced by a
      visual_quality-only advisory (`warning`) gate stage in `quality_gate.py`, plus a
      "Cosmetic Slopes" FDM guideline section. The "rotate" remedy already existed
      (`print_orientation.py` visual_quality mode); the gate just surfaces the residual.
      Deferred: slope-aware layer-height recipe hint (optional). The Greedy Look-Ahead Filter
      / chamfer-step transform was split out to the reverse-engineer-mesh item above.
- [ ] add textures capability https://github.com/Stone-Age-Sculptor/StoneAgeLib/blob/main/images/DemonstrationTexture.png
- [x] add a 90 deg dove tail joint. and a generalization: the angle is a parameter
- [ ] capability to import (and integrate) B-Rep files (.step. / stp, fcstd, .brep, .iges)
- [ ] feature: reverse engineer 3D mesh / point cloud into primitives. 
      (-> Differential geometry comparison) / "import" mesh files (.stl)

## Prior-art ideas
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
- [x] `cq_warehouse` (gumyr/cq_warehouse, 151 stars) -- strategy: pinned dep --
      already the project's `cq-warehouse` git dependency. No action.
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
- [x] cross-section preview rendering -- strategy: reimplement (basic centerline
      cuts Y/X/Z now in `preview.py`, wired into SKILL.md whole-part validation).
      Future enhancement: dimensioned slices, feature-specific detail sections.
- [x] `cq_debug_helpers.py` from thereprocase/cad-skill -- strategy: reimplement
      (catch silent boolean failures / workplane drift in `run_cadquery_model.py`).
      DONE via openspec change `runtime-boolean-verify`: reimplemented as `src/cq_verify.py`
      (`verify_boolean` / `verify_feature_bounds` / `check_workplane`), each raising a marked
      `RuntimeError` that `run_cadquery_model.py` maps to typed `silent_boolean` /
      `feature_overflow` / `workplane_drift` errors; prompt + reference guidance on when to
      wrap. `StepExporter` deliberately left out of scope.
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

