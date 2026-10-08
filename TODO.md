# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.

Each item below is a one-line pointer. Rationale, investigation notes, and
strategy discussion live in [Details](#details) at the end of this document,
linked from the item.

# V1.1.0
V1.0 is released. Completed tasks are in `documentation/DONE.md`.

## Test cases
- [ ] Salacia case
- [ ] [SUP Silencer](https://makerworld.com/de/models/2871437-paddleboard-sup-deflation-silencer#profileId-3205902)
- [ ] beamer-halter
- [x] Katzenwendeltreppe

## Defects
- [x] bridges are treated as overhangs -> ignore bridges of lengt l (l: printer parameter) -- `constraints.bridge_max_mm`, supported on >= 2 sides
- [x] arc fillets do not produce the intended result -- root-caused: not tessellation (folds survive 75x finer meshing) but hand-built tangent spandrel/prism fillets whose zero-thickness cusp runs past a tapered, chamfered rib; detected by the `sliver_fin` gate finding (`sliver-fin-detection` change). Remedy for authors: end the fillet where the wall is deeper than the fillet plus chamfers, or use `.edges(...).fillet()`
- [x] teardrop shaped holes not used -- `teardrop-hole-enforcement` change (prompt rule, `peak` param, lint + gate hint)

## Backlog

### Geometry / Blocks / Tools

- [ ] custom  support https://github.com/gittrahan/support-fins
- [ ] "parameter sets" not a full tool, but critical dimensions. LLM freely designs but gets a few constraints (e. g. gridfinity, gravitrax, lgego) (details)[#parameter-
- [ ] PCB Clip generator. instead of using screws to hold to PCBs in place comine standoffs and clip heads.
- [ ] Tool to create enclosures (for all major maker boards and cutouts for all widely used connectors
- [ ] tool to produce cable traces where cables are held press fit for 

### Skill improvement

- [x] cross section selection tool. important features should show up in the cross section
- [ ] generic parametric SCAD importer -> build blocks on the fly
- [ ] search tool for specific parametric cadquery / SCAD / build123d modells
- [x] evaluate [CQ-Kit](https://github.com/michaelgale/cq-kit) -- **REJECTED** (no reusable gap: exporters/ already covers STEP/IGES/STL/3MF/OBJ/SCAD, no history of boolean-fuse failures here so fuzzy booleans solve a problem we don't have, and selectors/XSection/Ribbon don't map to blocks/'s interface-aware primitive library; stale API surface too)
- [x] evaluate bernhard-42/jupyter-cadquery **REJECTED** -> not relevant
- [x] evaluate cq's assembly system and https://github.com/bernhard-42/cadquery-massembly -- **REJECTED** (already covered by `placement.py` / `mate_chain.py`); one optional spin-off: assembled multi-component STEP export -- [details](#cq-assembly-and-massembly)
- [x] show differences: https://github.com/bdlucas1/diff3d -- `src/diff_models.py` (boolean diff, JSON + PNG; no alignment, no diff3d dependency)
sets]
- [x] for selectors: evaluate https://github.com/voneiden/cq-filter and https://github.com/jmwright/selector_synthesis -- **REJECTED** (cq-filter's filter/sort/[] are native since CQ 2.4 and already in reference/; its only extras, group/last, need a Workplane subclass for little gain; selector_synthesis is a GUI click-to-selector research stub, and there is no picking step here)
- [ ] optimisation: https://github.com/yeicor-3d/dl4to4ocp
- [ ] Restructure to combat context creep -- [details](#context-creep-restructure)
- [x] Deduplicate pairwise-mirrored parts into one script/STL -- `copy_of` on a part (`dedupe-identical-parts` change) -- [details](#mirrored-parts-dedup)
- [x] A minimal deliverable for a parametric part -- `src/export_standalone.py` -> `standalone/` (`minimal-part-deliverable` change)
- [ ] "Activate" all necessary knowledge domains in the LLM -- [details](#knowledge-domain-activation-audit)

### Kinematic, Joints and Simulation

- [ ] Kinematic: ground/seating-plane check (lid-hits-floor) -- [details](#kinematic-ground-plane)
- [ ] Kinematic: articulated chains (a moving union carries other unions through the sweep) -- [details](#kinematic-articulated-chains)
- [ ] Joints: multi-DOF / coupled simultaneous movements -- [details](#joints-multi-dof)
- [ ] Blocks: assembly placeholder / keep-clear-for-assembly geometry -- [details](#blocks-assembly-placeholder)
- [ ] Joints: side-tagged `face_mount` docks for automatic union membership/axis derivation -- [details](#face-mount-docks)
- [ ] Anchors: BOSL2-style attachment helper for intra-part feature placement -- [details](#bosl2-style-anchors)
- [ ] HitsterTower: dovetail-corner-joint disassembly form fell outside the joints schema's single-rooted tree -- [details](#hitstertower-dovetail-form)
- [x] integrate a FEM-simulation for strength optimisation -- `src/fem_check.py` (`fem-stress-advisor`
      change): advisory only (never gates, never gets a quality_gate.py stage -- BC quality
      doesn't earn that yet), replaces `src/FEM.py`'s bounding-box-guessed stub
- [ ] `fem_check.py`: solve orthotropic instead of isotropic (currently applies FDM
      anisotropy only at the failure criterion, not the stiffness -- confirmed acceptable
      for a screening tool, but a real gap if the advisor is ever asked to do more)
- [ ] `fem_check.py`: source `material_properties.json`'s E/nu/allowables from measured
      filament data (own tensile tests, or a vendor datasheet) instead of literature-typical
      estimates
- [ ] `fem_check.py`: model boundary conditions as a real contact/fastener patch instead of
      a footprint-radius node selection around a declared interface -- a mis-declared
      anchor currently produces a confident wrong number (see `fem-stress-advisor` design.md
      risk list)
- [ ] fem: calculate required wall thickness step 1: global, step 2: regional (open question: how to do? slicer vs modell)
- [ ] fem: more infill only for compression load. infill direction = load direction (can I choose it arbitarily? if not: use part orientation) see: https://filamentfeed.com/article/designing-for-strength-3d-prints-june-2026

### Import / Export / View

- [ ] Export: 3MF print-plate structure (slicer-specific extension) -- [details](#export-print-plate-structure)
- [x] Export: automated 2D plate packing / bed nesting -- **REJECTED** (belongs in a slicer) -- [details](#export-plate-nesting)
- [ ] Preview: z-buffered renderer (removes painter's-algorithm shading artifacts) -- [details](#preview-z-buffered-renderer)
- [ ] Preview: render feature-detail previews more proactively -- [details](#preview-proactive-detail-renders)
- [ ] Reverse-engineer a 3D mesh / point cloud into primitives; import STL -- [details](#reverse-engineer-mesh)
- [ ] Import/integrate B-Rep files (STEP/STP, FCStd, BRep, IGES)
- [ ] Read back parameters on any user-initiated planning/authoring round
- [x] Bill of non-printed materials (BOM: screws, inserts, magnets, pins, adhesives) -- [details](#bill-of-non-printed-materials)
- [x] since orca slicer now supports STEP default to export this format

### Orthers

- [ ] cover more of the workflow (slicing, parameters, print)
- [ ] Accept Markdown / formatted UTF-8 text input
- [ ] Add textures capability
- [x] optimization for print speed
- [ ] Multi color / material support -- [details](#multi-color-material-support-claude-to-print)
- [ ] Engineering of multi-material interfaces and properties
- [x] User intent as an invariant over generation loops -- DONE (capture via
      `REQUIREMENTS.md`/`intent`, `intent`/`request_log` kept in sync by the `intent_ts`
      reconciliation gate, and every review now checks its render against `intent`/
      `request_log` as a second bar). The `parameter`-level routing rule is now a gate
      warning (`parameter-entry-routing-check`); remaining gaps in [details](#intent-as-invariant)
- [ ] Accept Markdown / formatted UTF-8 text input
- [ ] calculate and export slicer parameters such as: wall loops, infill, support, brim (auto brim in orca is terrible)

### Optimisation

- [x] 1. `measure_stl.py` `_thin_regions`: up to 3000 brute-force ray-vs-all-triangles casts in a Python loop, per union per wrapper run. Fix: batched `trimesh.ray` (embree/rtree) or chunked rays plus a bbox prefilter. Gain: very high
- [x] 2. Part script runs ~6x per gate (shim, `--deliver`, edge-treatment, feature-presence, toolpath-speed x2, Gridfinity) plus extra Python/`import cadquery` startups. Fix: memoize `_load_result` per (path, hash, rotate), merge the edge-treatment and feature-presence hooks into one load, let `--deliver` reuse the shim result. Gain: high
- [ ] 3. `quality_gate.py` runs once per union and re-runs the whole-model stages (kinematic, plate clearance, keep-out) each time, reloading every STL. Fix: run them once per model, or cache on manifest + plan hash. Gain: high on multi-part plans
- [ ] 4. `kinematic_check.py` sweep: per-pose `mesh.copy()` + `apply_transform`, full-resolution manifold booleans, 8 bisect steps x azimuths, STL reload and `CollisionManager` rebuild per entry. Fix: load/build once, set the fcl transform instead of copying, decimate or bbox-gate the boolean. Gain: high on plans with joints
- [ ] 5. `print_orientation.py` candidate loop (~0.5 s/candidate; 205 candidates = 107 s of a 129 s build). Topology caches and near-duplicate normal merging (5 deg) are already done, so the cost is per-pose. Profile: `_is_bridge` 52 s (about 754 regions/candidate; only ~10% pass the 80 deg gate but they pay a qhull `ConvexHull` with a `mkstemp` per call plus two `np.unique`, one with `axis=0`); `triangles_center`/`triangles.mean` recomputed per pose 3x/candidate, ~20 s plus a 6.5 s `triangles` gather (also behind `bed_contact_mask`, 17 s); `_overhang_angles` 4.6 s; `_build_height` 5.8 s. Fix: (a) base-mesh centroids once, per-pose centroid z = `centroids @ R[2] + tz`, shared by `bed_contact_mask` and `_is_bridge`; build the adjacency `keys`/`pairs` once per mesh, not per candidate; (b) in `_is_bridge`, gate all regions at once with `bincount` over component labels and loop only over survivors; replace `np.unique(edges, axis=0)` with 1-D edge keys; skip qhull for tiny regions (closed-form or numpy rectangle); (c) only if the profile shows support cost dominating and `_select` is monotone in it, prune candidates with a lower bound (true cost >= `BRIDGE_COST_FACTOR` x no-bridge cost). Before (b): histogram region face counts and line-profile one candidate. Gain: high
- [x] 6. `mesh_io.py` `_is_bridge`: Python dict of every edge plus per-edge Python loop per region, run in the gate and per orientation candidate. Fix: vectorize with sorted edge keys + `searchsorted` and numpy masks. Gain: medium-high (done in 522504b; remaining per-region overhead is tracked in item 5)
- [ ] 7. Repeated tessellation per union (3MF at 0.01, STL, shim default, preview per view) and a 0.01 mesh feeding all trimesh analysis. Fix: tessellate once for STL + 3MF, coarser tolerance (~0.02-0.05) for analysis STLs. Gain: medium, compounds with 1, 4, 5, 6
- [x] 8. `exporters/threemf_multi.py`: pure-Python `_weld`, one `ET.SubElement` per vertex/triangle, zip re-parsed for the manifold count. Fix: `np.unique` weld, join f-strings for XML, count from in-memory arrays. Gain: medium on large models
- [ ] 9. `preview.py`: per-triangle Python shading, per-triangle `verts[list(f)]`, re-tessellation per panel/section. Fix: vectorized `np.cross` shading, `verts[faces]`, tessellate once. Gain: medium
- [x] 10. Python-loop mesh helpers: `measure_stl._union_find`, `print_orientation._area_cumulation_normals`, `measure_stl._flat_faces`. Fix: `scipy.sparse.csgraph.connected_components`, `np.unique` + `np.add.at`, sorted-z `searchsorted`. Gain: medium, low effort

## Related ideas
Survey of external libraries/tools and whether/how to integrate each --
strategies defined in [Details](#integration-strategies).

### Parametric CAD library survey (2026-07)
- [ ] `vibe-cading` -- [details](#vibe-cading)
- [ ] `cadqueryhelper` -- [details](#cadqueryhelper)
- BOSL2 / NopSCADlib / MCAD -- reference only, no action -- [details](#openscad-libraries-reference-only)
- `bd_warehouse` -- reference only, no action -- [details](#bd_warehouse-reference-only)
- `cqparts` -- not adopted -- [details](#cqparts-not-adopted)
- [ ] `cqMore` and `cqterrain` -- [details](#cqmore-and-cqterrain)
- [ ] `partcad/partcad` -- [details](#partcad)

### Print orientation (Tweaker-3)
Clean-room reimplementation (GPL-incompatible upstream) -- see [details](#print-orientation-tweaker-3).
- [x] progressive overhang penalty (severity exponent `OV_H`)
- [ ] area-cumulation candidate generation as a fallback/supplement
- [ ] `min_build_height` / volume-minimization mode
- [x] `FIRST_LAY_H` band for bottom-contact (replaces tight `CONTACT_Z_EPS_MM`)

### CadQuery authoring guidance (jmwright/cadquery-llm-skill)

### Independent changes
- [ ] OCC deepcopy crash on print-orientation rotation -- [details](#occ-deepcopy-crash)
- [ ] cadgate-style gate checks (differential geometry + LLM intent-match) -- [details](#cadgate-style-gate-checks)
- [ ] `get_parameters`: extract customizable params from a script for parametric re-runs -- [details](#get_parameters)

### Benchmark corpora for `evals/`
Survey of prompt-to-result corpora usable to seed `evals/cases/` -- see [details](#benchmark-corpora-survey).
- [ ] SadilKhan/Text2CAD (blocked on a DeepCAD-sketch->CadQuery converter) -- [details](#text2cad)
- rundiwu/DeepCAD -- low priority, no action -- [details](#deepcad-no-action)
- mehsenazizi/mecagent-test -- low priority, no action -- [details](#mecagent-test-no-action)
- [ ] Metric: executability / syntax pass rate -- [details](#metric-executability-pass-rate)
- [ ] Metric: volumetric IoU / Dice (alongside `chamfer_mm`) -- [details](#metric-volumetric-iou)
- [ ] Metric: prompt-difficulty stratification -- [details](#metric-prompt-difficulty)
- [ ] Metric: efficiency (tool-calls / iterations / wall-clock) -- [details](#metric-efficiency)
- Not adopted: SmartAI/Chamfer's STEP geometry-kernel-oracle validity check -- overlaps `cq_verify.py`/`script_lint.py`

### From market research (documentation/market_research.md)
Central finding: LLM-CAD tools stop at "valid geometry" while printability
work lives in separate pipelines -- bridging them inline is this skill's
clearest opening. See [details](#market-research-survey).
- [ ] Diagnostics-as-assertions (cad-khana, FreeCAD-AI) -- [details](#diagnostics-as-assertions)
- [ ] Normalized Support Volume (NSV) score -- [details](#nsv-score)
- [ ] Orientation scoring (orient-stl) as a cross-check -- [details](#orientation-scoring-orient-stl)
- [ ] Iterative visual-feedback repair loop (CADReasoner, CADCodeVerify) -- [details](#iterative-visual-feedback-repair)
- [x] Print-friendly parameterizations: teardrop/bridged holes (Gridfinity) -- `teardrop-hole-enforcement` + `two-pass-print-finishing` (teardrops follow the accepted print pose) -- [details](#print-friendly-parameterizations)
- (covered by the cadgate-style item above) Verify-against-criteria tool (CadQuery-MCP)

### From intent-recognition research (documentation/intent_recognition.md)
Three capabilities: elicitation, scope classification, preservation. See
[details](#intent-recognition-survey) for the full framing and freeze-status
discussion. Items 1 and 3, the V1 defect fixes, have both shipped.
- [x] 1. Typed `request_log` entries (`level` + `targets`) -- DONE, `openspec/changes/
      archive/2026-09-01-typed-request-log/` -- [details](#typed-request_log-entries)
- [ ] 2. Spec audit with named ambiguity categories -- [details](#spec-audit-ambiguity-categories)
- [x] 3. Request-relative acceptance in the implementation audit -- DONE, `openspec/
      changes/archive/2026-09-01-request-relative-acceptance/` -- [details](#request-relative-acceptance)
- [ ] 5. Under-specified eval cases -- [details](#under-specified-eval-cases)

### From SmartAI/Chamfer's efficiency study (github.com/SmartAI/Chamfer @ a8f1c59, read 2026-08)
Head-to-head study found equal correctness at 5.9x lower cost / 3.2x lower
wall-clock than Claude Code, purely from context/output/round-trip discipline.
See [details](#smartaichamfer-study) for the full study summary and negative
results.
- [ ] 1. Per-attempt efficiency telemetry -- [details](#efficiency-telemetry)
- [ ] 2. Failure-mode mining -> environment-facts prompt block -- [details](#failure-mode-mining)
- [ ] 3. Fold verification into the build call -- [details](#fold-verification-into-build-call)
- [ ] 4. One reconciliation pass, from measured values -- [details](#one-reconciliation-pass)
- [ ] 5. Render economy (scoped to agent self-inspection renders) -- [details](#render-economy)
- [ ] 6. Output-token economy -- [details](#output-token-economy)
- [ ] 7. Assumption pinning -- [details](#assumption-pinning)
- [ ] 8. Warm kernel process -- needs measurement first -- [details](#warm-kernel-process)
- [ ] 9. Context-surface audit -- [details](#context-surface-audit)
- [ ] 10. Eval method: held-out set, pre-registered bars -- [details](#eval-method-held-out-set)

### From related_projects.md high-rated entries (2026-08)
Survey rows rated `High`/`Medium-High` not yet tracked as TODO items
(SmartAI/Chamfer, already `High`-adjacent, is fully covered above).
- [ ] CadAgent: token budget management for the part loop -- [details](#cadagent-token-budget-management)
- [ ] CadAgent: smart clarification policy (assume + state default, don't always ask) -- [details](#cadagent-smart-clarification-policy)
- [ ] CadAgent: undo/rollback via automatic snapshots -- [details](#cadagent-undo-rollback-snapshots)
- [ ] harnesscad: pre-kernel geometry-aware verification -- [details](#harnesscad-pre-kernel-verification)
- [ ] Text2CAD (MLYengineering): rule-bound repair patches + cross-attempt failure learning -- [details](#text2cad-mlyengineering-repair-and-learning)

---

## Details

### C5 compass language
Investigate "compass language" `.\debug\image-1786538590774.png` shows the
problem: east should be right. Reason: mixing up "Viewed from South" and
"south facing" under observation.

**Re-confirmed 2026-09-08** (`debug/session-2026-09-08.md`, round 10). The user
asked for "fillet on the east side"; the skill had to stop and `AskUserQuestion`
which end is East, *again* -- the fifth round in this project's history to
re-litigate it (rounds 8, 9, 10 explicitly). The user's answer: "I am looking at
plate_preview.png 'Front' which per convention is 'viewing from south': the R8 is
on the left 'West' side. previously we mixed up the naming conventions."

Root cause, now pinned:
- `prompts/planning.md:3-14` hardwires **East = +X**, North = +Y, and defines the
  standard views by compass station.
- This project's real-world anchor is the *opposite*: `BUILD_PLAN.json`'s
  `request_log` carries "East = right side of the ashtray.jpg photo = X=0 (near
  the yellow mark), matching parameters.py convention", and `parameters.py` has
  `BEZEL_EAST_CORNER_FILLET_MM` commented "East (right/X=0 side)". So in this
  project East points in **-X**, 180 deg from the skill default.
- There is **no `BUILD_PLAN.json` field that records a project's resolved
  axis->compass binding.** The `feature-vocabulary` spec mandates that the skill
  *use* compass prose and echo ambiguous references back before acting (which the
  session did), but that is a per-turn patch: nothing persists the resolution, so
  every new correction round re-derives "East" from either the prompt default or
  the buried photo note and can land on either end. The `2026-08-07-rotation-clock-vocabulary`
  change fixed rotation *direction* words (clockwise/counterclockwise), not the
  base axis<->compass binding.
- Secondary contributor: "viewed from south" (a camera position) vs "south face"
  (a face whose outward normal is -Y) are distinct and were conflated in the
  reasoning. On the South viewing station (+X to the viewer's left) the photo's
  "right side" maps to -X, which is exactly the project's "East" -- the skill's
  own convention would call that West.

Fix (proposed): a `coordinate_frame` object in `build_plan_schema.json`, e.g.
`{"east": "-x", "north": "+y", "up": "+z"}`, written at Phase 1 exit whenever the
user's frame differs from the `prompts/planning.md` default, defaulting to the
standard binding when absent. Every checkpoint-prose and review step reads it
instead of assuming +X. `plan_validate.py` emits an advisory finding (the
`check_block_thinness` tier) when `planning_notes`/`request_log`/`intent` prose
contains a compass term and no `coordinate_frame` is recorded. This is prose- and
review-frame only; it does not touch `placement.rotate` / joint `dof.direction`
sign conventions, which stay right-hand-rule on the literal axes.

### C5 hinge ear center-vs-edge
The hinge ear shows an old problem: placing primitives with their center
aligning to the other part's edge -- see `.\debug\image-1786540203166.png`.

Investigated (transcript: session `b6ac548d...`, `session-export-1786538430013.zip`,
round 9's final `cradle.py`). Exact code:

    EAR_STANDOFF = 5.0
    PIVOT_Z = BAR_H + EAR_STANDOFF          # 8.5 + 5.0 = 13.5
    RISER_DEPTH = 4.0
    riser = car_box(x, TONGUE_WIDTH,
                    PIVOT_Y - RISER_DEPTH, RISER_DEPTH,   # Y 1.0 .. 5.0
                    BAR_H, EAR_STANDOFF)                  # Z 8.5 .. 13.5
    knuckle = ....center(PIVOT_Y, PIVOT_Z).circle(KNUCKLE_R)   # r=2.6 at (5.0, 13.5)

Both of the riser box's far faces land exactly on the disc's CENTER, not on its
tangent: top face Z=13.5 == PIVOT_Z, +Y face Y=5.0 == PIVOT_Y. The disc spans
Z 10.9..16.1 and Y 2.4..7.6, so its lower-rear quadrant is swallowed by the riser
and only the upper-front quarter stands proud -- the "half-buried disc on a boxy
step" in the render. Bbox Zmax 16.1 in the preview footer confirms this is the
shipped geometry.

The correct riser tops out at the tangent line: `PIVOT_Z - KNUCKLE_R` (10.9), i.e.
height `EAR_STANDOFF - KNUCKLE_R` = 2.4, and its Y-band should be centered on
PIVOT_Y rather than ending there. The error is not a missing constant -- it is
reusing the pivot literal for a boundary that owes it a +/- radius offset.

Notes for the fix: (1) nothing in the pipeline can see this -- the union is
watertight, volume/faces/bbox are all plausible, no DFM rule is violated; only
the rendered preview shows it, which is why it survived to round 9. (2)
`script_lint`'s AST pass cannot catch it either: `car_box` is a script-local
helper, so the checker would have to know that args 5+6 form a Z-band and that
the same name feeds a `circle()` center. (3) The tractable fix is the
`anchor()`/`place_at()` API in [BOSL2 attachables](#bosl2-attachables) -- make
"tangent of this body" the only way to express the join, so center-as-edge
cannot be typed. A cheap partial detector: after a union, flag when an added
body's overlap with the existing solid exceeds ~20% of its own volume (here the
knuckle loses ~25%), but that also fires on legitimately embedded pins.

**Re-confirmed 2026-09-08** (`debug/session-2026-09-08.md`). `verify_seated` was
merged Sep 1 (commit 51dc097) as a construction-time guard **the part script must
call**, plus a `prompts/part.md` rule routing knuckle hinges through
`blocks.joints.pin_hinge`. The Sep 8 re-run edited `EAR_STANDOFF` 5.0 -> 6.0 in
the same hand-rolled `cradle.py` and rebuilt clean. `grep -n "verify_\|pin_hinge"
build/cradle.py build/plate.py` -> zero matches: the script predates the fix, was
only ever edited in place, and was never regenerated under the new guidance.
Nothing in `script_lint.py` / `quality_gate.py` fails a script for *lacking* the
guard, so an old hand-rolled knuckle passes with the same center-vs-tangent bug
latent. Needs the retrofit lint in [C5 fixes did not take](#c5-fixes-did-not-take-2026-09-08).


### C5 knuckle pivot ping-pong
The llm totally did not get that making the knuckle stand of the cradle's
feet more does not mean that the plate's knuckle has to move upward (+Z).
Probable cause: in the authoring pose the inference is correct, but when the
cradle is moved into its assembled pose it's not.

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
-> Ask clarifying question when parameters have the same value if they are the same or different measures. should they mate or not. e. g. 3 holes have the individually stated diameter of 5 mm. ask " should all holes have the same diameter (one parameters) or may they differ? Or a user asks for a rectangular feature and specifies both dimensions with the same value. ask if it should be constraint to quadratic or not.

**Re-investigated 2026-09-07** (same transcript, tool-call level). Three findings
sharpen the above; the first is the actual defect, the last is what is still
unfixed.

*The ping-pong is a within-round regression, not just a cross-round wobble.*
Round 9 authored three mutually incompatible geometries in a single session:
(9a, `Edit` at transcript line 128/133) keep `PIVOT_Z = 6.0` and add a
Y-direction neck `STANDOFF_Y = PIVOT_Y  # 5.0`; (9b, line 164/167) revert that
and restore a Z riser `EAR_STANDOFF`, moving `cradle.py`'s `PIVOT_Z` back to
13.5; (9c, line 179) hand-edit `plate.py`'s `PIVOT_Z` from 6.0 to 13.5 "to
match". Step 9c silently undid round 8's *user-requested* correction ("move the
hinge knuckles on the plate down to where they were, aprox 8mm from the lower
end") -- the round-8 rationale comment was deleted in the same edit. The final
message to the user states it plainly: "plate.py PIVOT_Z moved to 13.5 to match,
since it's the same shared pin -- I updated both files."

*The user's round-9 wording was relative; it was applied as absolute.* "they
need to extend up when viewed from west. 3mm (plate thickness) + 2 mm because
the bore hole sits 2 mm behind the plate" constrains the *standoff* (a 5 mm
offset derived from the plate's own stack). It was converted into a move of the
shared axle's absolute Z in the car frame, which is what dragged `plate.py`
along.

*The sanctioned mechanism existed and was never reached.* The strings `joints`,
`root_part`, `kinematics`, and `pin_hinge` appear **zero** times in the entire
session transcript, for a model whose two parts are joined by a real revolute
filament-pin hinge. `prompts/planning.md` rule 7 (cross-part matched pair ->
`joints` entry) and rule 9 (a folding leaf closing onto its plate ->
`kinematics` with `stop_on_contact: true`) both cover this case exactly, and
`blocks.joints.pin_hinge` carries `emits: [leaf_a, leaf_b]` plus a revolute
`dof` -- so `mate_chain.py` would have *derived* the plate's pose from the
cradle's, and the second `PIVOT_Z` literal would not exist. Nothing forced it:
rules 7 and 9 are prose only, and `plan_validate.py` can validate a `joints`
entry but cannot notice one is *missing*.

Cause (1) is now covered on the orchestrator side: the parameter-scope routing
rule added with typed `request_log` entries (`skill/phase3_build.md`,
`openspec/specs/request-log/`) forbids hand-editing a shared literal into a
sibling part and names this failure. What is still uncovered is the carrier that
made the hand-edit look necessary -- the duplicated literal itself, which is
established at *plan* time and is invisible to every gate: the plan declares the
same physical bore as an `interfaces[]` entry on both parts, `plan_validate.py`
explicitly permits the same interface `name` on two parts ("the part id
disambiguates them"), and `feature_presence_check.py` asserts each part's
`position_mm` only against *its own* authored frame, so two independently-typed
copies of one bore both pass. Fix (implemented,
`openspec/changes/archive/2026-09-07-shared-interface-derivation/`): a plan-time advisory finding
(`plan_validate.check_shared_interfaces`, printed after `BUILD_PLAN OK`, not a
hard error) when one interface `name` appears on two parts that no `joints` entry
links.

Still open: the folded-pose constraint itself. "when the leg
lies flat on the front plate" is a coincidence assertion (two bores coaxial) at
a pose that is not any part's authoring pose. `kinematic_check.py` sweeps for
interference and range, not for feature coincidence at a pose, so the assertion
was discharged by hand rotation math in prose -- which visibly failed inside the
transcript ("that requires sin(theta) = 2, which is impossible") and then got
re-derived differently each round. Cheapest future home for it: an assertion on
an existing `kinematics` entry evaluated at its `stop_on_contact` pose, reusing
`kinematic_check.iter_poses`. Deferred -- it depends on the plan carrying a
`kinematics` entry at all, which is what the advisory nudges toward.

**Re-confirmed 2026-09-08** (`debug/session-2026-09-08.md`). `check_shared_interfaces`
was merged Sep 7 (commit 814e329). It keys on **one `interfaces[].name` held by two
parts that no `joints` entry links**. The C5 plan:

    plate  interfaces = [None, None]      # interfaces[].name is null on every entry
    cradle interfaces = [None, None]
    joints = None   root_part = None   kinematics = None

so the check has no non-null name to match on and finds nothing. The Sep 8 re-run
then raised `cradle.py` `PIVOT_Z` 13.5 -> 14.5 (`EAR_STANDOFF` 5 -> 6) and left
`plate.py` at 13.5 per the user's explicit "don't touch plate!" -- producing two
non-coaxial bores for one physical pin, with no gate objection. This is the exact
class 814e329 was written to stop; it just cannot see an *unnamed* duplicated
literal. Needs the broadened check in
[C5 fixes did not take](#c5-fixes-did-not-take-2026-09-08). (Note: the "don't touch
plate" instruction is itself correct -- the plate bore is fixed by the plate's own
physical stack. The right resolution is a `joints` entry so the plate pose is
*derived*, making the second literal impossible, not a hand-mirror.)

**Eval coverage added** (`openspec/changes/expand-eval-corpus-hard-cases/`):
`evals/cases/hinged-latch` (joints+kinematics+shared pivot, guards the knuckle
pivot-ping-pong class), `evals/cases/lid-thickness-correction` (seeded round-2
correction), and `evals/cases/east-side-mount` (compass-wording conflation)
now give the scorecard a signal for this failure class. The product fixes
below (`coordinate_frame`, hand-rolled-hinge lint, broadened
`check_shared_interfaces`, `/retrofit`) are still unimplemented.

### C5 fixes did not take (2026-09-08)
`debug/session-2026-09-08.md` re-ran the C5 Phone-Holder skill (a small design
change: east-side fillet + raise the knuckle bore). All three C5 defects above
reproduced despite each having a merged fix. **One root cause:** every fix is
*prospective* -- it takes effect only when a part is re-planned or re-authored
under the new guidance. C5 is a long-lived plan edited incrementally since July;
its `BUILD_PLAN.json` and both part scripts predate all three fixes, and nothing
in `plan_validate.py` / `script_lint.py` / `quality_gate.py` fails a project for
*missing* the new guard. Evidence per fix is in each section above.

**Items 1-3 landed 2026-09-11** (`openspec/changes/archive/2026-09-11-absence-lints-and-coordinate-frame/`).
Item 4 (`/retrofit`) is still open.

Proposed retrofit work (all advisory, `check_block_thinness` tier -- printed after
`BUILD_PLAN OK`, never a hard `plan_invalid`):

1. **Per-project compass binding.** Add `coordinate_frame` to `build_plan_schema.json`
   (`{east,north,up}` each one of `+x/-x/+y/-y/+z/-z`, default = the
   `prompts/planning.md` standard binding). Write it at the Phase 1 exit
   checkpoint when the user's frame differs. `plan_validate` warns when compass
   terms appear in `intent`/`planning_notes`/`request_log` and no
   `coordinate_frame` is recorded. Checkpoint-prose and review steps read it.
   Prose/review only -- does not touch `placement.rotate` sign conventions.

2. **Hand-rolled-hinge lint.** In `script_lint.py` (or a `quality_gate` stage):
   when the plan describes a revolute/pin hinge (or two parts hold a round
   interface at the same world position) and a part script builds a cylinder
   union without `verify_seated` / `verify_backed` / `pin_hinge`, emit a warning
   naming `cq_verify.verify_seated` and the `blocks.joints.pin_hinge` route.
   Makes the opt-in guard's *absence* visible on a pre-existing script.

3. **Unnamed shared-literal detection.** Broaden `plan_validate.check_shared_interfaces`:
   also flag when two parts declare round interfaces of the same `diameter_mm` at
   the same world position (after `placement`) with no linking `joints` entry,
   even when `name` is null. Plus: warn when a multi-part plan whose
   `intent`/`request_log` describes a hinge/pivot/fold has `joints: null`.

4. **Retrofit prompt.** A `/retrofit` (or Phase 0 sub-step) that, on an existing
   project, runs 1-3, reports what the current plan/scripts lack, and offers to
   add the missing `coordinate_frame` / `joints` entry / `verify_*` calls before
   any correction round proceeds. Cheaper than re-planning from scratch and stops
   the "fix merged, still broke" loop for every project already in flight.

### C5 quality-gate overhang authored frame
`quality_gate._analyze_stl` ran `mesh_io.overhang_metrics` on the STL as written
by `write_assembly.py` -- the part's authored / `placement` frame -- and never
applied the chosen print orientation's rotation. `print_orientation.py` (run
earlier in Phase 3) evaluates overhang at the real print pose; the gate did not.
So whenever the optimizer rotates a part away from its authored pose, the gate's
`overhang_exceeded` warning describes a face that is bed-supported (or a vertical
wall) in the pose that actually prints. Logged in `MEMORY.md`
(`skill_gap_quality_gate_overhang_authored_frame`) since 2026-07-20, re-confirmed
six times, including both parts on the 2026-09-08 C5 re-run (plate: "Worst
overhang 90.0 deg over 466.1 mm2" on the cap underside that becomes a wall in the
cover-face-down print pose).

**FIXED 2026-09-08.** `_analyze_stl(stl_path, overhang_deg, rotate=None)` now
takes the orientation's `rotate` steps; `run_gate` threads
`(orientation or {}).get("rotate")` into it; the mesh is posed via
`placement.to_matrix({"rotate": rotate})` before `overhang_metrics`. Tests:
`tests/test_quality_gate.py::test_authored_frame_overhang_cleared_by_print_orientation`,
`::test_run_gate_threads_orientation_rotate_into_overhang`. Behaviour note:
`worst_location_xyz_mm` in the overhang issue is now reported in the build frame,
not the authored frame. The cradle's real overhang (elevated leg/ear undersides,
identity print orientation) is unaffected and still reported.

### Silica Tray support claim
LLM claims "no support needed" despite "support score 654.1" which might be
wrong. Test result: small overhangs like this can be printed without support.

**Root cause found and FIXED 2026-09-15.** `quality_gate._emit_print_recipe`'s
`recipe["supports"]` was hardcoded `False`, unconditionally, regardless of
`orientation["support_score"]` (a weighted overhang-area cost from
`print_orientation.py`, not a support/no-support verdict) or of any
`overhang_exceeded` finding the gate had just emitted for the same STL. So the
delivered `print_recipe` always told the LLM "no support needed" even when the
gate had flagged an overhang moments earlier -- there was nothing to "get
wrong" downstream; the field simply never read the analysis. `support_score`
itself is left as a ranking signal only (used by `print_orientation.py` to pick
the least-overhang pose among candidates) and is not a support/no-support
threshold on its own -- a small nonzero score, as here, can still print clean,
matching the session's test result. Fix: `run_gate` now computes
`needs_support = any(overhang_exceeded warning in all_issues)` and threads it
into `_emit_print_recipe`; an `overhang_exceeded` downgraded to `info` by a
declared `clearance_opening` (see [Hitstertower oversupport](#hitstertower-oversupport))
does not set it. Tests:
`tests/test_quality_gate.py::test_print_recipe_supports_true_when_overhang_exceeded`,
`::test_print_recipe_supports_false_when_self_supporting`,
`::test_print_recipe_supports_false_when_overhang_downgraded_to_info`.

### Silica Tray re-export coincidence
"I just re-derived the print orientation and re-exported so the deliverables
and BUILD_PLAN.json match your hand-edited dimensions: 6mm triangle pitch,
1mm rib width, 20mm total height." Works, but is it by design or just
coincidence?

**Investigated and FIXED 2026-09-15.** Traced the deterministic pipeline
`skill/phase3_build.md` documents: Design approval -> Print-orientation
optimization -> Model export -> Quality gate -> Phase 4 deliver. Every step is
written as a linear, once-per-session sequence with no cross-reference for what
happens when a user asks for a change *after* Phase 4 already reported
delivery -- a very ordinary flow (this session, and the C5 sessions above, both
did it). Nothing in `skill/*.md` named that case, so whether the LLM re-ran
orientation/export/gate was pure judgment -- verified as it did here, but
nothing stopped a future session from hand-editing `build/<id>.py` and
reporting "done" against a stale `model.3mf`/STL/`print_recipe`. (The
mechanism that would have silently caught it for a *standalone*
`uv run python build/build.py` re-run -- `build_template.resolve_orientations`
comparing `orientations.json`'s `source_script_hash` stamp against the current
script -- only covers that later, out-of-session path; it says nothing about
what this session itself must do before calling a correction delivered.)
Fix: added a "Post-delivery corrections" section to
`skill/phase3_build.md` after the Quality gate section, naming the rule
explicitly -- a correction after delivery re-opens print-orientation (for the
affected union only), model export, and the quality gate before Phase 4's
delivery report repeats. Prompt-only change; no code to test.

### Hitstertower oversupport
LLM did not get the intent of the opening on the bottom of the tower (finger
can reach in to pull card out). Instead insisted on fully supporting the
south wall. This is not necessary because the load is the mobile phone on
top, which is hardly more than 200g. This weight can be supported by a 1cm
support on both sides of the wall.

**Investigated 2026-09-08 -- transcript not in `debug/`.** The two Hitster
exports on disk are `session-export-1786343198762.zip` (2026-08-10, an OpenSCAD
attempt interrupted right after the failure-mode question -- never reaches
planning) and `session-export-1786431095406.zip` (2026-08-12, the
dovetail-disassembly rebuild). Neither contains a bottom finger-access opening
or a south-wall support argument: the 08-12 rebuild reduced the base to
`plate + raised platform + 4 mortise sockets` (`build/base.py`, no card-exit
cut) and made every wall a plain flat panel, so the opening question never came
up. This item therefore records a takeaway from a session whose transcript
isn't archived -- attach it for a tool-call-level pass like the C5 items.

What can still be said from the design and the current pipeline:

*The opening is functional negative space, and nothing types it.* The HitScan
tower is a card dispenser: the arch-shaped cut at the bottom of one wall is a
hand-access / card-exit port, not a defect. `interfaces[]` only covers positive
mating features; an in-part void that must stay open (hand access, card exit,
vent, cable pass-through) has no typed home, so nothing in the plan tells the
gate "do not close this, do not bridge/support across it." Same shape of gap as
[assembly placeholder / keep-clear](#blocks-assembly-placeholder) and the
keep-out-zone concept, but for a void inside a single part rather than a
between-parts clearance volume.

*The support verdict is purely geometric.* A wall with a large opening near its
lower edge presents the material spanning above the opening as an unsupported
overhang/bridge, so `mesh_io.support_cost` (weighted by `SUPPORT_EXPONENT`) and
`quality_gate.py`'s `overhang_exceeded` both push toward "add support."
`print_orientation.py` treats strength as orientation-neutral (always 1.0) and
has no load-vs-support trade-off, and the overhang checks carry no notion of
what actually carries the load. So the LLM, with no structured way to assert
"the opening is intentional and the ~200 g phone on top is carried in
compression by the two wall columns flanking it, ~10 mm each side is plenty,"
deferred to the gate's geometric finding and argued for full support.

*The load argument has a home already; the "keep it open" half does not.* The
structural claim (10 mm of column each side is enough for 200 g) is exactly a
`parts[].engineering_rationale` `load_path` entry (`prompts/part.md` block) --
state the assumption, don't add a gate. The missing piece is a way to mark the
opening as a required void so the support/overhang findings bounding it drop to
advisory.

Fix direction (cheapest first):
1. DONE (prompt-only): `prompts/planning.md` rule 5a records a user-described
   access/exit/clearance opening as an `interfaces[]` entry with
   `type: "clearance_opening"` plus a `part_notes` load-path note. No schema
   change (`interfaces[].type` is a free string; `feature_presence_check.py`
   skips unknown types). This alone gives Phase 3 the structured hook it was
   missing when it argued for support.
2. DONE 2026-09-15 (partial): `quality_gate._clearance_opening_zones` maps each
   `clearance_opening` interface's `position_mm` through the part's `placement`
   and the chosen print orientation's `rotate` into the same build frame as
   `overhang_metrics`' `worst_location_xyz_mm`; `_analyze_stl` downgrades an
   `overhang_exceeded` finding to `severity: "info"` when its worst face falls
   within the opening's radius (half-diagonal of `size_mm` + margin), and points
   the hint at the part's `engineering_rationale`/`part_notes` load path instead
   of "add chamfers or redesign". This reads the interface directly rather than
   routing through the keep-out-zone export (below) -- cheaper for the overhang
   check alone, since it only needs one point + radius, not a meshed zone. The
   `support_cost` / `print_orientation.py` half (excluding the zone from the
   orientation optimizer's ranking, not just the gate's report) is still open --
   that one plausibly does want the keep-out-zone route since it needs an actual
   volume to subtract, not just a point check.

### Project regeneration prompt
Export a prompt which allows the human user to re-generate the whole project
from scratch with a new LLM session (improved LLM, new skill, other skill,
etc). The prompt must include the latest changes, user intent, all
user-provided measurements, drawings and all other artifacts.

DONE. `src/regen_prompt.py` (stdlib only) serializes the approved `intent`,
the verbatim `request_log` (with each entry's `level`/`targets`/`images`),
`parameters.py` inlined whole, the `sketches/` file list, the print target,
and the previous parts/joints decomposition labelled reference-only, into
`REGENERATE.md`. Phase 4 step 6 runs it on every delivery, so the file always
reflects the latest corrections (`intent` is rewritten per correction by
Phase 3's intent-rewrite rule). Images cannot be inlined -- the prompt lists
their paths and tells the user to re-attach them.

### Engineering rationale consolidation
The engineering rationale lives only as an `ENGINEERING RATIONALE` comment block in
each part script, so an N-part model spreads it across N files. Nothing reads it:
`plan_validate.py`, `script_lint.py` and `quality_gate.py` have no notion of it, both
authoring paths (raw and archetype template) carry their own copy of the insertion
rule and the load-bearing trigger list, and it is absent from `README.md` /
`REGENERATE.md`, which are rendered from `BUILD_PLAN.json`.

DONE 2026-09-08: the rationale moves to `BUILD_PLAN.json`'s
`parts[].engineering_rationale`, written back in Phase 3 and validated at the
pre-export `plan_validate.py --require-rationale` run. Change:
`openspec/changes/archive/2026-09-08-consolidate-engineering-rationale/`.

### Context creep restructure
Restructure to combat context creep. Reference: `ARCHITECTURE.md`. Options:
- like openspec: phases are own commands, user interaction at the end
  (change, restart), then start new phase
- python script owns the loop and switches context & models; prompt will be
  split
- use sub-agents / workers for each phase

### Kinematic ground plane
Explore adding one simple ground/seating plane (lid-hits-floor checks);
surrounding-geometry questions stay out of scope (external simulation).

### Kinematic articulated chains
Articulated chains (a moving union carries other unions through the sweep).

### Joints multi-DOF
Multi-DOF / coupled simultaneous movements. A joint is a LIST of
single-axis movements (`rotate`/`translate`, each with axis + reference
vector + range); independent movements for now. A spherical/ball joint is
two coupled `rotate` movements sharing a center -- listing them as two
independent entries models a 2-axis gimbal, NOT the ball's coupled cone.
Capture coupling (e.g. helical screw pitch, ball cone) as a later field.

### Export print-plate structure
Separate unions into print-plates. Today all unions compile to one "world"
result and `write_assembly` already writes each as a separately named 3MF
`<object>` with `plate` metadata. Core 3MF has no native print-plate concept
(objects + `<build><item>` only); true multi-plate assignment is a
slicer-specific extension (Bambu/Prusa project-3MF). Decide: emit the slicer
plate structure, or leave plate split to the operator.

### Export plate nesting
Automated 2D plate packing / bed nesting. Distinct from the print-plate item
above (that is about 3MF plate *structure*); this is about *deciding which
part goes on which plate and where*, which today is declared manually in the
plan. Prior art: thereprocase/cad-skill Phase 4 -- rasterize each union's XY
footprint at 0.5mm/px (PIL), precompute 0/90/180/270 rotations, bottom-left-
fill largest-area-first, keep uniform spacing via `scipy.ndimage.binary_dilation`
on the blocked bitmap, build compound plates with OCC (`BRep_Builder` +
`TopoDS_Compound`), export STL+STEP per plate, report bed utilization %.
Inputs we already have: per-union assembled/print-oriented STLs, `plate`
metadata, bed size (would need to come from `profile.json` -- not
currently a field). Decide scope: full nester, or just a utilization report +
overflow warning leaving assignment to the operator/slicer. Interacts with
print-orientation (footprint depends on chosen orientation) and the
plate-clearance check (spacing == the one-layer-height fuse rule).
Reimplement (PolyForm-safe; algorithm only). Additional prior art:
thereprocase/snuggle-demo (https://github.com/thereprocase/snuggle-demo) -- a
standalone "stuffing"/nesting algorithm demo, worth checking against the
bottom-left-fill approach above.
**REJECTED** -- this feature belongs into a slicer.

### cq assembly and massembly
Evaluated 2026-09-22. **REJECTED** for the pipeline's core.

`cadquery-massembly`: its feature is mates -- named coordinate systems snapped
together to derive poses down a chain. That is `mate_chain.compute_mate_poses`
(62 lines): `world(B) = world(A) @ dock_A @ inv(dock_B)`, walked outward from
`root_part`, with `plan_validate._check_joints` guaranteeing a tree first so no
cycle handling is needed. MAssembly's reason to exist is driving animations in
jupyter-cadquery; this pipeline has no viewer, it has trimesh sweeps
(`kinematic_check.py`). Trading 62 owned lines for a dep tied to an unused
viewer stack is a loss.

`cq.Assembly`: three reasons against.
1. Nothing to solve. `constrain()`/`solve()` is a numerical optimizer for
   under-specified constraints; `BUILD_PLAN.json` declares every `dock` and
   `placement` explicitly, so poses are exact composition. An optimizer would put
   a non-deterministic step underneath gates that are currently reproducible
   (`kinematic_check`, `plate_clearance_check`, `keep_out_check`).
2. Covers half the consumers. `placement.py` must yield both a CadQuery transform
   (`apply_cq`) and a numpy 4x4 (`to_matrix`) from one JSON dict, because
   everything downstream of `write_assembly` is trimesh, not OCCT. `to_matrix` stays
   either way. And `apply_cq` deliberately goes straight to
   `BRepBuilderAPI_Transform` on `.wrapped` to dodge the `cq_warehouse.extensions`
   deepcopy patch -- an Assembly `Location` path would re-enter that.
3. Wrong contract. Parts are authored by separate sub-agents into separate scripts
   whose `result` is a `Workplane` or `dict[str, Workplane]`, and each part prints
   separately. `plan_validate.py` already rejects a top-level `assembly` key on
   purpose.

One spin-off worth keeping: `cq.Assembly.save("x.step")` writes a
multi-component STEP with per-component names and colors. STEP is currently
per-part (`exporters/step.py`); there is no assembled STEP for CAD handoff. If
wanted, that is a standalone ~15-line exporter in `write_assembly.py` -- build a
throwaway `cq.Assembly`, `.add(wp, loc=Location(matrix), name=part_id)` using the
poses already computed, save. No constraints, no solver, no schema change. Add it
when someone actually asks to open the model in FreeCAD/Fusion.

### Blocks assembly placeholder
Assembly placeholder geometry. A block may declare PSEUDO geometry marking
the volume that must stay clear to ASSEMBLE it (e.g. a hinge's pin-insertion
path / leaf-swing-during-assembly envelope). It is exempt from export (not
printed) and from the kinematic sweep (not a moving body), but other geometry
must not intrude into it or assembly is blocked. Pairs with the mating-area
footprint (2D where-to-connect) -- this is the 3D keep-clear-for-assembly
volume. The gate should flag real geometry that violates a declared
placeholder. Distinct from the model's own clearance gaps.

**Implementation note -- suppress support/overhang cost over a declared void
(from [Hitstertower oversupport](#hitstertower-oversupport)).** The
`clearance_opening` interface type lands in the plan (`prompts/planning.md`
rule 5a). Two suppressions were planned:
- `quality_gate.py` `_analyze_stl`: DONE 2026-09-15 -- downgrades an
  `overhang_exceeded` finding to advisory (severity `info`) when its
  overhanging faces bound a declared `clearance_opening`, message pointing at
  the interface's load-path note instead of "add chamfers or redesign". Reads
  `interfaces[].position_mm`/`size_mm` directly (a point + radius check), no
  keep-out zone export needed for this half.
- `mesh_io.support_cost` / `print_orientation.py`: still open -- subtract the
  down-facing area whose supporting ray passes through the zone before
  reaching the bed. This one plausibly wants the keep-out-zone route below
  (an actual volume to subtract from the ray-through-zone test, not just a
  point-in-radius check).
The structural half (is 10 mm of wall each side enough for the stated load?)
stays a `parts[].engineering_rationale` `load_path` entry -- no new gate.
Remaining scope question for the `support_cost` half: extend the existing zone
export (`units.resolve_keep_out` -> `keep_out__<name>.stl` -> `keep_out_check.py`)
so a part can emit `result["keep_out"]` tagged as an opening, vs. a distinct
`opening` key (keep-out zones are currently checked for *intrusion by other
parts*; an opening is checked for *nothing* -- it only suppresses).

### Bill of non-printed materials
Implemented via `openspec/changes/bill-of-non-printed-materials` (archived
once merged): a hand-authored top-level `bom` array (`item`, `spec`, `qty`,
`parts`, `note`), an `inventory.json` `supplied_hardware` marker on
hardware-consuming blocks driving an advisory validate finding, a Phase 2
summary table, and a Phase 4 "Hardware to buy" section. `planning_notes`
category (c) now holds the assembly procedure only.

### Face mount docks
Side-tagged `face_mount` docks so the planner derives union membership and
the world joint axis automatically (interface naming: keep assembly/mating
docks conceptually distinct from kinematic axes even though both live in the
block `interfaces` array).

### Preview z-buffered renderer
matplotlib mplot3d has no z-buffer and depth-sorts whole triangles
(painter's algorithm), so flat faces show cosmetic triangular shading
patches where angled wall/fillet triangles paint over coplanar ones.
Geometry and normals are correct (STL/3MF watertight + winding-consistent);
the artifact is preview-only. Switching `preview.py` to a z-buffered
renderer (trimesh + pyrender / `Scene.save_image`) removes it, at the cost
of an OpenGL dependency that `preview.py`/`mesh_io.py` currently avoid by
design.

### Preview proactive detail renders
Render feature detail previews more proactively. The `--detail` capability
exists (`render_preview.py`/`preview.py` render a high-res zoomed view +
optional cross-section per named feature; wired in SKILL.md Step 3 "Feature
detail previews"), but in a live run detail previews were not generated for
small/critical features by default -- only on explicit request or the
complexity-gate path. Decide when the skill should auto-render a detail
preview (e.g. every interface/joint feature, or any feature below a size
threshold vs. the whole-part bbox) so small features are actually
inspectable without the user asking, and make SKILL.md prescribe it rather
than leave it to judgement. (Deferred from the orientation/overhang fix
session.)

### BOSL2-style anchors
BOSL2-style attachment/anchor helper for INTRA-part feature placement
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
GPL-incompatible, see [Integration strategies](#integration-strategies)).

Concrete failure instance (C5 Phone-Holder session, cradle.py's hinge
knuckle, see [C5 hinge ear center-vs-edge](#c5-hinge-ear-center-vs-edge)
above): a connecting box's edge coordinate was set equal to a circle's
CENTER coordinate (reusing the shared pivot variable for both), instead of
offset by the circle's radius to its tangent line. Booleans still succeeded
(watertight), so nothing caught it -- only a rendered preview crop showed the
knuckle as a disc half-buried in a boxy step instead of a free-standing round
ear on a slim neck. `anchor()`/`place_at()` should make "offset to this
body's tangent/edge, not its center" the default so this class of bug can't
be expressed by accident; `script_lint`'s AST-only checks can't catch it
since it requires tracing which named constant plays which geometric role
(center vs. edge) across two different primitives.

### Reverse-engineer mesh
Reverse engineer 3D mesh / point cloud into primitives
(-> differential geometry comparison); "import" mesh files (.stl). See also
https://github.com/Stone-Age-Sculptor/StoneAgeLib/blob/main/images/DemonstrationTexture.png
for the related textures capability.

### HitsterTower dovetail form
From HitsterTower ("D:\Code\cq-design\debug\session-export-1786431095406.zip"):
"Hinges -> dovetail corner joints. All 4 pin_hinge kinematic joints are gone.
Each corner is now a dovetail_corner_joint (4 pins/tails per corner, 3mm
board thickness, 6mm tooth insertion depth, 0.1mm clearance for separable
fit). The tower no longer folds -- it fully disassembles at all 4 corners
into 4 flat panels + base for storage, and presses back together for use.
Polarity: every wall carries pins on its east edge, tails on its west edge,
so the ring closes consistently (wall_a->wall_c->wall_b->wall_d->wall_a)."
Couldn't express this as a formal top-level `joints` mate-chain (the schema
requires a single-rooted tree; a 4-panel ring produces conflicting/
double-anchored paths) -- so each wall keeps its own explicit placement, and
the dovetail mating is declared through each wall's `interfaces` instead.
Functionally equivalent, just not chained through the schema's joint-tree
mechanism.

### Mirrored parts dedup
Plan states that parts are pairwise mirrored. LLM generated two files:
"wall_a vs wall_b: You're right -- I over-built. wall_b.py is geometrically
identical to wall_a.py (same width, same tenon, same dovetail parameters,
both symmetric). I copied it into a separate file out of habit
(BUILD_PLAN.json lists 5 distinct part ids), but a symmetric flat panel
mirrored is the same printed part -- nothing to design twice. I should
delete wall_b.py and just have the export use wall_a's STL for both
positions (printed twice). Want me to do that now? It also means correcting
BUILD_PLAN.json so wall_b references wall_a's geometry instead of carrying
its own script."

### Intent-based prompt reformulation
DONE -- same artifact as the re-generation prompt above ([Project regeneration
prompt](#project-regeneration-prompt)) and as
`documentation/intent_recognition.md` item 4
([Canonical intent restatement](#canonical-intent-restatement)), which shipped
as `REQUIREMENTS.md` (`skill/phase1_requirements.md`, `openspec/changes/
capture-requirements-spec/`). No separate reformulation prompt needed --
resolved by that same artifact.

DONE. The reformulation itself is `BUILD_PLAN.json`'s `intent`: written and
approved at the Phase 1 exit checkpoint, copied verbatim by Phase 2, rewritten
in place whenever a Phase 3 correction changes the design, and used as the
request-conformance bar in review. Delivered by
`openspec/changes/approved-intent-reformulation/`; the export half is the
regeneration prompt above.

### Intent as invariant
Question resolved 2026-08-29: yes, adopting the OpenSpec-style flow (user
states an intent -> skill asks enough questions to write a spec -> the spec
drives generation) was a good idea, and it shipped as `REQUIREMENTS.md`
(Phase 1 writes it; Phase 2 amends it in place; see [Canonical intent
restatement](#canonical-intent-restatement) and `openspec/changes/
capture-requirements-spec/`).

That closes the *capture* half. Three further changes close the *invariant*
half:

- `openspec/changes/archive/2026-09-21-intent-staleness-gate/`: `BUILD_PLAN.json`'s
  `intent_ts` field plus `plan_validate.py`'s `check_intent_reconciled` block a plan
  whose `request_log` has a `clarification`/`correction` newer than the last
  reconciled `intent` rewrite -- `intent` can no longer silently drift stale
  relative to the log (sync enforcement).
- `openspec/changes/archive/2026-09-01-typed-request-log/`: `request_log` entries
  gained optional `level`/`targets` fields, so an entry can be scoped to a specific
  part instead of matched by keyword.
- `openspec/changes/archive/2026-09-01-request-relative-acceptance/`: both the
  autonomous implementation audit and the progressive inline self-review now check
  the delivered render against `intent` + the entries scoped to that part
  (`prompts/audit.md` group 3, `render_prompt.py`'s `scoped_request`) as a second,
  advisory-unless-also-blocking acceptance bar (conformance checking).

Together these close what the earlier draft of this item called items 1 and 3 of
`documentation/intent_recognition.md`'s gaps 2-3 ([Typed request_log
entries](#typed-request_log-entries), [Request-relative
acceptance](#request-relative-acceptance)) -- the generation loop's output is now
checked against `intent`/`request_log`, not only against the plan's structure.

What is still open, narrowly:
- (closed by `openspec/changes/parameter-entry-routing-check/`: a `parameter`-level
  entry appended with `--snapshot-scripts` is diffed by `quality_gate.py`, which warns
  `routing_violation` on an untargeted, non-joint-linked script change -- advisory
  only, so it does not yet stop the C5 sibling-literal edit, only surfaces it);
- promotion of advisory request-conformance findings to blocking-by-default is
  still eval-gated and undone (item 5, [Under-specified eval
  cases](#under-specified-eval-cases));
- `REQUIREMENTS.md` itself (as opposed to its `intent` mirror in
  `BUILD_PLAN.json`) is still never read by any gate or agent.

Update (change `intent-staleness-gate`): the mechanical half is closed -- the plan's
`intent_ts` stamp plus a blocking `plan_validate.py` check fail any plan whose
`request_log` has moved past the last reconciliation of `intent`. Still open: a
model-level conformance bar before delivery, promoting request-conformance findings from
advisory to blocking (eval-gated), and the ambiguity re-audit of mid-build corrections.

### Knowledge domain activation audit
Audited `documentation/Knowledge Domains.md` (an external survey of what a
text-to-CadQuery LLM needs: 3D/B-Rep/CSG spatial reasoning, the fluent
CadQuery API + selectors, mechanical/DFM engineering, NL intent
disambiguation, and a three-part execution/feedback loop -- exception
mapping, geometric validation, visual verification) against what this skill
already injects and enforces. Finding: **already substantially activated**
for every domain except NL intent, which was already the subject of a
separate, deeper survey.

Per domain, what already exists:
- **Spatial reasoning / B-Rep / CSG**: `reference/CadQuery Pattern
  Reference.md` (workplane naming, selector semantics, transforms) +
  `reference/CadQuery Anti-Patterns.md` Tier 1 (kernel-level: booleans, wire
  closure) and Tier 2 (stateful-context: origin drift, `.workplane()` local
  coords) -- injected into `prompts/part.md` as `{{CADQUERY_REFERENCE}}` for
  every part.
- **Fluent API / selectors**: same Pattern Reference file's `## Face & Edge
  Selectors` section -- the doc's own recommended remediation for "selector
  hallucination" ("RAG over CadQuery docs") is exactly what this injection is.
- **Mechanical engineering / DFM**: `reference/FDM 3D Print Design
  Guidelines.md` + `reference/Engineering Design Rules.md`, both injected as
  `{{FDM_GUIDELINES}}`/`{{ENGINEERING_RULES}}` in `prompts/part.md` and
  `prompts/planning.md`; SKILL.md's DFM constraints table duplicates the
  load-bearing numbers for main-session checks.
- **Execution/feedback loop**: `run_cadquery_model.py`'s JSON contract is the
  doc's sketched `execute_cadquery_code`, `quality_gate.py`'s bounded
  `claude -p` fix loop is its self-correction loop, `cq_verify.py` adds
  construction-time assertions the doc only gestures at.
- **Exception/stack-trace mapping**: SKILL.md's `## Error handling
  reference` table maps every OCC exception class the doc names
  (`Standard_ConstructionError`, `BRep_API command not done`,
  `StdFail_NotDone`, `Standard_NullObject`, `Standard_OutOfRange`,
  `Standard_TypeMismatch`) to a typed error + hint -- more granular than the
  doc's sketch.
- **Topological/geometric validation**: `mesh_io.py` watertightness +
  `run_cadquery_model.py`'s `geometry` block (bbox, volume, face count)
  cover this; the multi-union/thin-wall checks go beyond what the doc
  describes.
- **Visual verification**: `preview.py`/`render_preview.py` +
  `reference/Visual Review Checklist.md`, applied at both progressive-build
  and autonomous-audit checkpoints (`skill/phase3_build.md` Step 4).

Remaining gap, the doc's failure-mode-table row "Fillet & Chamfer Crashes --
radius >= adjacent edge length": `prompts/part.md`'s "Fillet/Chamfer Safety"
line states the rule as prose but nothing checks it *before* the OCC call
the way `cq_verify.py` checks *after* a boolean -- already tracked under
[harnesscad pre-kernel verification](#harnesscad-pre-kernel-verification); no
new item needed.

The doc's "Domain-Specific NLP" row (intent disambiguation, hierarchical
decomposition) is the one domain NOT covered by reference-file injection --
Phase 1's topology clarification is narrow (shape ambiguity only). This is
already the subject of a full separate survey; see
[Intent-recognition survey](#intent-recognition-survey) for the five-item
breakdown (typed `request_log`, ambiguity-category audit, request-relative
acceptance, canonical intent restatement, under-specified eval cases) -- no
new item needed here either.

Net: this bullet is closer to DONE than open. What's actually left under it
collapses into the two already-tracked items above; keeping it as a
separate top-level bullet risks double-tracking the same gap under three
names. Recommend closing this bullet at the next TODO pass and letting the
two linked items carry the remaining work.

### Integration strategies
Integration strategy per item avoids the native-vs-MCP false binary.
Options, by how much they preserve upstream updates while staying
self-contained and inline (no MCP):
- **reimplement** -- own code; no upstream updates; on-design.
- **pinned dep** -- declare as a uv git/pip dep, call from a thin `src/`
  adapter; updates via `uv lock --upgrade-package` (same as the existing
  `cq-warehouse` dep); self-contained via the committed lock.
- **vendored snapshot** -- copy source into the repo with license + recorded
  upstream SHA + a documented refresh procedure; manual updates.
- **optional external** -- native by default, use the external tool if
  present, degrade with a warning otherwise (same pattern as
  `kinematic_check.py` without `python-fcl`); off the critical path.

### Gear geometry
lwidm/cq_gears -- strategy: optional external -- DONE. Parametric involute
spur/helical gear generator for CadQuery. Fails the license test for pinned
dep / vendored snapshot: upstream declares no license (`license: null`), and
this project is PolyForm Noncommercial, so bundling isn't safe. No gate
check applies either (nothing is installed or called natively to degrade),
so the integration point is the planning prompt: rule 13 in
`prompts/planning.md` tells the LLM to note in `planning_notes` and point to
the repo as a downloadable resource when a design needs gears, instead of
inventing gear geometry from scratch. Also added to the README Prior-art
table.

### Parametric CAD library survey
GitHub survey of reusable OpenSCAD/CadQuery/build123d model libraries (2026-07),
rated for usability as `src/blocks/` additions. Full ratings table in
session history; summary below. Confirms `cq_warehouse` (already a pinned
dep) is the strongest direct-reuse candidate; everything else is
reference-only or needs hand-porting.

#### cq-gridfinity
michaelgale/cq-gridfinity, 200 stars, active -- strategy: reimplement
(blocks) -- pure CadQuery, narrow domain. Teardrop/bridged-hole DFM pattern
already tracked under [Print-friendly parameterizations](#print-friendly-parameterizations);
no separate action beyond that item.

#### vibe-cading
fa-mc/vibe-cading, 5 stars, active -- strategy: reimplement (blocks) --
CadQuery + LLM-agent-oriented typed-parameter part classes (screws, gears,
joints, bearings, heat-set inserts, hinges, standoffs); closest
philosophical match to this skill's block pattern. Low stars/immature --
cherry-pick specific parts as reference when adding new blocks, not a
dependency.

#### cadqueryhelper
medicationforall/cadqueryhelper, 25 stars, active -- strategy: reimplement
(blocks) -- small CadQuery primitive helpers, borrow individual functions if
needed.

#### OpenSCAD libraries (reference only)
BOSL2 (BelfrySCAD/BOSL2, 2252 stars, very active), NopSCADlib
(nophead/NopSCADlib, 1602 stars), MCAD (openscad/MCAD, 681 stars) --
OpenSCAD, not Python; no direct import possible. Reference only for
formulas/dimensions (threading, gears, standard-part sizes) when a new block
needs a formula `cq_warehouse` doesn't cover. No action.

#### bd_warehouse (reference only)
gumyr/bd_warehouse, 96 stars, active -- build123d, not CadQuery; the
actively-maintained successor to `cq_warehouse` with broader
fastener/thread/gear/pipe coverage. Reference only (hand-port on demand)
since the kernel wrapper API doesn't match. No action.

#### cqparts (not adopted)
cqparts/cqparts, 148 stars, unmaintained since 2020 -- wrapper framework,
assembly abstraction conflicts with this skill's direct-Workplane block
pattern. Not adopted.

#### cqMore and cqterrain
`documentation/Block_Sources.md`, rated High usability -- no repo link or
star count recorded in the source survey; re-find and evaluate before
deciding reimplement vs pinned dep.

#### partcad
`partcad/partcad` (`documentation/related_projects.md`) -- package manager
for hardware/manufacturable products across CAD kernels (CadQuery,
build123d, OpenSCAD). Adoptable: package-manager framing for versioned part
definitions with declared metadata (parallels `blocks/inventory.json`), YAML
assembly format tracking BOM/part relationships, caching rendered models to
speed iteration. Not evaluated for adoption strategy yet (reimplement /
pinned dep / reference-only).

### Print orientation Tweaker-3
One change -- strategy: reimplement. Clean-room native port of the
orientation formulas. Tweaker-3 is GPL-3.0 and this project is PolyForm
Noncommercial; bundling (pinned dep / vendored snapshot) is
license-incompatible, so we reimplement the algorithm (formulas are not
copyrightable) and do NOT copy the GPL code or its verbatim tuned constants
-- derive our own. Touches `print_orientation.py` + `mesh_io.overhang_metrics`,
tested via `test_print_orientation.py`.

### CadQuery authoring guidance
jmwright/cadquery-llm-skill, one change -- strategy: vendored snapshot.
Doc-only; vendoring a doc snapshot is the upstream-recommended usage, so no
design conflict. Record the upstream SHA and refresh periodically. Upgrades
`reference/` and `prompts/part.md`.

Done (change `add-cadquery-anti-patterns`): anti-patterns integrated as
`reference/CadQuery Anti-Patterns.md` (kernel / stateful-context /
API-mechanic tiers, always-injected) plus fluent recipes folded into the
pattern reference and three contradictions reconciled. Free Function API
(`cadquery.func`) content deliberately excluded -- this pipeline is
fluent-only.

### OCC deepcopy crash
`debug/occ-error.md`: rotating certain B-rep solids (seen in
`build/plate.py`, an axle bore spanning an open slot, or a pure-45-deg
pocket ceiling with no flat cap) crashes inside cq_warehouse's
deepcopy-based `Shape.copy()` -> OCC `BinTools` serialization round-trip
(`Standard_Failure: BinTools_SurfaceSet::ReadGeometry: UnExpected
BRep_PointRepresentation = 42`, sometimes flaky). Currently worked around by
avoiding the triggering geometry shapes (documented in `occ-error.md`), root
cause not fixed. Leads to investigate: replace cq_warehouse's deepcopy copy
with OCC's native `BRepBuilderAPI_Copy`; or make `write_assembly.py` rotate
the trimesh (mesh-based) for print-oriented 3MF objects instead of the
B-rep, sidestepping the deepcopy path entirely (the kinematic-check STLs
already do this).

### cadgate-style gate checks
Strategy: optional external (off the critical path; gate runs natively,
cadgate augments when present). Differential geometry (volume/bbox/wall
delta vs base) reimplemented in `quality_gate.py`; the LLM intent-match is
the part that justifies the optional external path.

### get_parameters
Extract customizable params from a script for parametric re-runs
(CadQuery/cadquery-contrib mcp-server) -- strategy: reimplement (tiny).

### Chamfer-distance metric
DeepCAD evaluation metric: Chamfer distance for golden-mesh regression tests
-- strategy: reimplement (trimesh already computes it). Done: `chamfer_mm`
in `evals/run_evals.py`, matched to golden parts via
`scipy.optimize.linear_sum_assignment` over shape descriptors. See the
[benchmark corpora survey](#benchmark-corpora-survey) for what should feed
it.

### Benchmark corpora survey
`documentation/related_projects.md` text-to-CAD datasets. Of the ~119
surveyed projects, five are actual prompt-to-result *corpora* (not just
technique ideas) that could seed `evals/cases/`. Rated for adoption as a
benchmark below.

#### Text-to-CadQuery corpus
arXiv 2505.06507; rows "Text-to-CadQuery (arXiv 2505.06507 + code)" and
duplicate "Text-to-CadQuery/Text-to-CadQuery" -- **High**. ~170k
text->CadQuery code pairs, native CadQuery format, zero conversion cost --
runs through `run_cadquery_model.py` unmodified. Already the origin of the
`chamfer_mm` idea. Gap: nobody has sampled a subset into `evals/cases/` yet.
Strategy: reimplement a small corpus-import script that filters the 170k
down to this skill's domain (enclosures/brackets/plates/adapters -- not
organic/decorative shapes), executes each script to produce `golden/*.stl`,
and writes `request.md` from the pair's description.

#### WKJBryan/cadquery-library
**High, complementary**. 2600+ native CadQuery examples, hand-curated (vs.
Text-to-CadQuery's auto-generated 170k) -- better signal-to-noise for a
small eval corpus, less coverage. Same import strategy as above; adopt in
full given the smaller size.

#### Text2CAD
SadilKhan/Text2CAD + duplicate Text2CAD (DFKI / NeurIPS) -- **Medium**. Real
multi-level (beginner->expert) text-difficulty annotations that this skill's
own corpus lacks, but the paired geometry is DeepCAD sketch-extrude JSON,
not CadQuery -- needs a converter that doesn't exist today (closest analog,
`convert_build123d.py`, targets a different kernel). Worth the
prompt-difficulty tiers even if the geometry pairs are skipped; blocked on
the converter.

#### DeepCAD (no action)
rundiwu/DeepCAD -- **Low**. Same non-CadQuery format problem as Text2CAD,
without even the text pairing -- it's the substrate Text2CAD is built on,
not independently useful. No action beyond what Text2CAD covers.

#### mecagent-test (no action)
mehsenazizi/mecagent-test-Mehsen-AZIZI -- **Low**. Take-home-exercise scope,
too small to be a corpus; its IOU eval idea duplicates rawwerks/VibeCAD's
(already noted there). No action.

#### Metrics to add
Alongside the existing first-shot pass rate / attempts-to-pass /
`chamfer_mm` / cost-per-part in `evals/run_evals.py`, in priority order:

##### Metric executability pass rate
Fraction of a corpus's scripts that run without error on attempt 1. This is
the metric the Text-to-CadQuery paper itself reports, so it's the natural
apples-to-apples number when citing that corpus. Strategy: reimplement (the
wrapper's `success`/`errors` fields already carry this per attempt; just
aggregate).

##### Metric volumetric IoU
(rawwerks/VibeCAD row) -- add alongside `chamfer_mm`, not instead of it:
Chamfer averages surface distance and can look fine when a small protrusion
or hole is simply missing, which IoU catches directly. Strategy: reimplement
via `trimesh.boolean` intersection/union on the same centered, matched mesh
pairs `run_evals.py` already produces.

##### Metric prompt difficulty
Prompt-difficulty stratification (SadilKhan/Text2CAD's beginner->expert
tiers) -- bucket eval cases by description complexity and report pass
rate/chamfer per tier instead of one flat scorecard, so degradation on terse
vs. detailed requests is visible. Depends on the [Text2CAD](#text2cad) corpus
item above (or hand-tagging the existing/new cases).

##### Metric efficiency
Tool-calls / iterations / wall-clock per case (SmartAI/Chamfer row,
sidbalasubramanian007/Aipex-Lab-Research row) -- `attempts-to-pass` already
exists in `run_evals.py`; add raw tool-call count and wall-clock alongside
cost/part so loop-efficiency regressions (not just correctness regressions)
show up in the scorecard. Superseded/expanded by
[Efficiency telemetry](#efficiency-telemetry) below.

Explicitly not adopted: SmartAI/Chamfer's STEP geometry-kernel-oracle
validity check overlaps what `cq_verify.py`/`script_lint.py` already do at
construction time, so it wouldn't add a new failure class here.

### Market research survey
`documentation/market_research.md`: recent LLM-CAD / parametric /
FDM-printability projects surveyed 2023-2026. The central finding: LLM-CAD
tools stop at "valid geometry" while printability work (support,
orientation, self-supporting design) lives in separate pipelines -- bridging
them inline is this skill's clearest opening. Items below are the reusable
primitives, not whole-tool adoptions.

#### Diagnostics-as-assertions
cad-khana, FreeCAD-AI -- one change -- strategy: reimplement. cad-khana
(`github.com/cyberchitta/cad-khana`) is a Claude Code skill / build123d
wrapper that emits a structured `diagnostics.json` (overhangs, wall
thickness, clearances, interferences) and turns geometric constraints into
build-failing assertions (`assert_min_wall`, `assert_clearance`,
`assert_no_interference`). This is the closest analog to our gate; extends
`quality_gate.py`.
- geometric constraints as build-failing assertions feeding the structured
  `{source, severity, type, message, hint}` contract the gate already emits
- per-project FDM design-rule file (FreeCAD-AI's `AGENTS.md`/`FREECAD_AI.md`
  pattern, e.g. "min wall 1.2mm, all edges >=0.8mm fillet") consumed by the gate

#### NSV score
Normalized Support Volume score (SEG / ODPO, arXiv 2511.16434) -- one change
-- strategy: reimplement. NSV = support-material volume / model volume: a
scale-invariant printability cost (validated against Cura, Pearson r > 0.85
on 50 Thingi10k models). SEG itself is a diffusion model with no public
code; only the *metric* is reusable. Pairs with the Tweaker-3
print-orientation work ([details](#print-orientation-tweaker-3)) (NSV scores
a given orientation).
- NSV as a quantitative gate score / orientation-selection objective in
  `print_orientation.py` (support volume from the overhang+bed-projection model)

#### Orientation scoring orient-stl
Folds into the Tweaker-3 change -- strategy: reimplement.
`github.com/sameer/orient-stl` finds best FDM orientation via DIRECT global
optimization (sub-second). Overlaps the existing Tweaker-3 item; the
overhang-area + slice-count fitness from the build-orientation research
(genetic-algorithm, connected-components, "Part Orientation Fused Shape
Optimization") is the reusable scoring function.
- overhang-area + slice-count fitness as an alternative/cross-check
  candidate score alongside the Tweaker-3 formulas

#### Iterative visual-feedback repair
CADReasoner, CADCodeVerify -- one change -- strategy: reimplement.
CADReasoner (CVPR 2026) and CADCodeVerify (arXiv 2410.05340) close a render
-> diff -> regenerate loop: render the part, auto-generate validation
questions, answer them against the render, feed discrepancies back. We
already render previews (`preview.py`) and run a bounded `claude -p` fix
loop in the gate; this adds the visual-discrepancy signal to that loop.
- feed multi-view preview renders + auto-generated check questions into the
  gate's correction prompts (currently text-only DFM/geometry findings)

#### Print-friendly parameterizations
cq-gridfinity / Gridfinity practice -- strategy: reimplement (blocks).
`github.com/michaelgale/cq-gridfinity` and the wider Gridfinity ecosystem
encode concrete DFM heuristics: "lite" thin shells for less material,
bridge-over (teardrop) magnet/screw holes, variable wall thickness.
Block-library additions, not a gate change.
- teardrop / bridged horizontal holes in `blocks/connectors.py` +
  `blocks/fasteners.py` so bosses and ports stay self-supporting

#### Verify-against-criteria tool
CadQuery-MCP `verify_cad_query` -- strategy: optional external.
`github.com/rishigundakaram/cadquery-mcp-server` exposes a `verify_cad_query`
validator that checks geometry against natural-language criteria. The LLM
intent-match overlaps the [cadgate-style item](#cadgate-style-gate-checks);
same optional-external rationale (native gate runs without it, augments when
present).

### Intent-recognition survey
`documentation/intent_recognition.md`, surveyed 2026-08, split into three
capabilities: **elicitation** (detect an under-specified request and ask),
**scope classification** (what kind of change is asked for, and what may it
touch), **preservation** (does the delivered geometry still satisfy the
user's own words). The skill does elicitation narrowly (topology +
dimensions, Phase 1 only), records intent well (`request_log`), does no
scope classification, and audits every part against the PLAN rather than the
request -- so a plan that misread the request passes every gate. Items
ordered by value/cost; item 1 is the precondition that makes 2 and 3 cheap.
Prior art: ProCAD (arXiv 2602.03045) clarify-then-generate for
text-to-CadQuery, LLM4CAD-Editor (arXiv 2606.20607) functional/operation/
parameter intent levels, CADDesigner (arXiv 2508.01031) requirement-analysis
stage.

Freeze status (`Feature freeze for V1.0`, 12.08.2026): items 1 and 3 target
logged, reproduced failures (the C5 cradle ping-pong; the audit being blind
to the request) and are arguably defect fixes; 2, 4 and 5 were slated as
features for the next version. **Update 2026-08-29:** item 4 was pulled
forward into V1 anyway (see [Canonical intent restatement](#canonical-intent-restatement))
-- the capture half was cheap (a docs-only Phase 1 addition, no schema or
script change) and closes a real gap in what ships. 2 and 5 remain deferred
to the next version; not decided here.

#### Typed request_log entries
DONE -- `openspec/changes/archive/2026-09-01-typed-request-log/`. `level`
(`functional` | `operation` | `parameter`) and `targets` (part ids + named
features/parameters) are optional fields on `request_log` entries
(`src/build_plan_schema.json`, `openspec/specs/request-log/`), settable via
`log.py request add --level --target` and filterable via `log.py request
search --level --target` (`src/log.py`). `render_prompt.py`'s
`section_cuts` re-keys the Step 3 extra-section tiering off `targets` when
present, falling back to the keyword match only for untyped legacy entries.

The routing rule the label exists for (a `parameter`-level entry may not
silently change a sibling part's independently-typed constant -- the C5 cradle
failure class) is a `quality_gate.py` warning via
`openspec/changes/parameter-entry-routing-check/` (`log.py request add
--snapshot-scripts` baseline + `routing_violation`). It is advisory: promotion to
blocking needs eval evidence.
#### Spec audit ambiguity categories
One change -- strategy: reimplement (ProCAD). Generalize Phase 1's topology-
clarification rule (shape ambiguity only) into an audit over a fixed
category list, and re-run it on mid-build corrections, where ambiguity is
most expensive because parts already exist. ProCAD's contribution is asking
ONLY when necessary -- a rule that fires on every request is worse than
today's; the question budget and the skip-entirely escape hatch (as the
dimension checkpoint already has) are load-bearing. Category-named prompting
beats a bare "ask if unsure" (arXiv 2504.12113).
- categories: topology (exists), missing dimension, conflicting constraint,
  unstated reference frame (the C5 compass-language defect), unstated
  fit/load, part-vs-assembly scope
- one question per ambiguity under a hard budget, keeping the existing named
  either/or discipline -- extends `skill/phase1_requirements.md`, no new phase
- re-audit a mid-build correction before acting on it
  (`skill/phase3_build.md` correction handling)

#### Request-relative acceptance
DONE -- `openspec/changes/archive/2026-09-01-request-relative-acceptance/`.
Both the autonomous implementation audit and the progressive inline
self-review now carry a "Request conformance" question class (group 3 in
`prompts/audit.md`): the approved `intent` (falling back to the
`request_log` `initial` entry) plus every entry scoped to the part via
typed `targets` or a keyword match (`render_prompt.py`'s `scoped_request`),
fed to the reviewer as `REQUEST_TEXT`. A `no` there is `severity: advisory`
-- it does not fail the review or consume a retry -- unless the same
discrepancy also fails a group 1/2 (plan-conformance/universal) question, in
which case it is `severity: blocking` with the request text cited as
supporting evidence. The no-script rule is unchanged: the auditor still
never receives the part script. Promotion of advisory findings to blocking
by default remains eval-gated and has not been done -- that is item 5,
[Under-specified eval cases](#under-specified-eval-cases).

#### Canonical intent restatement
DONE 2026-08-29 -- strategy: reimplement. Merges two standing items ("intent
based prompt reformulation", "regenerate the whole project from scratch with
a new LLM session"): a frame-explicit, user-confirmed restatement of what is
being built, carried forward and updated as corrections land. Also the
natural input to [Request-relative acceptance](#request-relative-acceptance)
and the structural fix for compass-language defects -- restatement forces
the reference frame to be written down instead of assumed.

Shipped as `REQUIREMENTS.md`, a project-root artifact beside `parameters.py`
(resolving the "where it lives" question in favor of a sibling file, not a
plan field): intent, confirmed topology reading, dimensions, fit
requirements, resolved DFM constraints, and open questions/assumptions.
`skill/phase1_requirements.md` writes it at the same checkpoint as
`parameters.py`; `skill/phase2_planning.md` amends it in place if planning
introduces or changes a requirement (bounded role, `planning_notes`-style
current-state-only -- not a changelog). See
`openspec/changes/capture-requirements-spec/` for the proposal and spec
delta.

Deliberately deferred (see that change's `design.md`): no quality-gate
presence check yet (mirrors how `parameters.py`'s own gate check shipped as
a separate follow-up change after the convention existed), and it is not
yet wired into [Request-relative acceptance](#request-relative-acceptance)
or the reference-frame check the compass-language defect needs -- those
still require the auditor to actually read and check against this file,
which is the remaining work under [Intent as invariant](#intent-as-invariant).

#### Under-specified eval cases
One change -- strategy: reimplement (gating cost). Every case in
`evals/cases/` is well-specified, so none of the above can regress and the
existing scorecard cannot see it. This is the gate on the whole idea, not an
afterthought.
- cases whose `request.md` is deliberately under-specified in each named
  category, scored on whether the right question was asked
- well-specified controls scored on NOT asking -- without them the metric
  rewards asking about everything
- `evals/run_evals.py` scoring + `tests/test_eval_corpus.py`

### SmartAI/Chamfer study
github.com/SmartAI/Chamfer @ a8f1c59, read 2026-08. Chamfer is a TypeScript
CAD agent over a build123d MCP server. Its `benchmarks/` directory is the
interesting part: a four-arm head-to-head (Chamfer v0/v1, Claude Code,
Codex) on a held-out set, same model, same MCP server binary for every arm,
graded by a geometry oracle on the exported STEP. Result: equal correctness
at **5.9x lower cost and 3.2x lower wall-clock than Claude Code** -- 6.5 vs
9.2 agent turns, 2,232 vs 9,849 output tokens, ~53k vs ~433k context tokens
read per run.

The gain is explicitly NOT model, kernel, or a cleverer algorithm. Their own
decomposition (`benchmarks/analysis/v0-weaknesses.md`, 21 graded runs):
**~46% of cost is output tokens** (on the hardest case 55% of those are
hidden reasoning), ~33% cache write, ~21% cache read; latency splits ~68%
LLM / ~32% tool. So the levers are (a) how much context is read per turn,
(b) how many output tokens are emitted, (c) how many tool round-trips happen
at all -- in that order. Verification was measured to be **cheap** (~15% of
cost) and is not a lever.

Negative results from the same study, worth as much as the positives -- do
not repeat them:
- **Global thinking=low**: <20% cost saving, dropped checks on two cases.
  Rejected.
- **"Complexity-scaled" verification** (skip the reconciliation pass on
  simple parts): worse on cost AND correctness than not doing it -- one case
  collapsed to 8/15 with an over-claim. Recorded lesson: "verification is
  not overhead to scale away; on interacting-feature parts it is the
  cheapest part of the run."
- Their pattern card (23 mined idioms) was bundled with the two changes
  above, so its own effect is **unmeasured** -- treat it as untested, not as
  proven.
- Standing method rule they adopted after drifting: one intervention at a
  time, each traced to a weakness observed in real run transcripts,
  pre-registered metric movement per change.

Items below are ordered by value/cost. Item 1 is the precondition: none of
the rest can be shown to work without it. (Their STEP geometry-kernel oracle
stays not-adopted, per the [Benchmark corpora survey](#benchmark-corpora-survey)
above -- `cq_verify.py`/`script_lint.py` already cover that failure class.)

#### Efficiency telemetry
One change -- strategy: reimplement. `build/attempts.jsonl` records
`prompt_chars` and `model` and nothing about what the attempt actually cost.
Chamfer's entire analysis is a decomposition our log cannot produce. This
supersedes and fills in [Metric: efficiency](#metric-efficiency) above (raw
tool-call count + wall-clock); the split below is what made their table
actionable.
- `telemetry.py`: optional `tokens` (`in`/`out`/`cache_read`/`cache_write`),
  `cost_usd`, `wall_ms`, `llm_ms` vs `tool_ms`, `tool_calls`,
  `failed_tool_calls` -- all OPTIONAL, existing logs must stay valid
  (`tests/test_telemetry.py`)
- per-tool table: calls, mean duration, result payload size (chars/image
  tokens) -- their finding was that one tool (`render_view`) was 11.5% of
  suite wall for zero model changes, which is invisible without
  payload/duration per tool
- failed-call retry cost: time from a failed call to the next successful
  attempt (they measured ~6% of suite wall lost to 15 failed calls across
  52% of runs)
- `evals/run_evals.py`: aggregate the above into the scorecard next to
  `first-shot rate` / `attempts-to-pass` / `chamfer_mm`, so a loop-efficiency
  regression is visible without correctness moving

#### Failure-mode mining
One change -- strategy: reimplement. Their single biggest robustness win was
four sentences of environment facts in the system prompt, each traced to a
counted failure (missing `from build123d import *`; calling MCP tool names
inside the sandbox; blocked builtins; wrong `expected` schema). That killed
11 of 15 failed tool calls. Our equivalent facts (what the wrapper injects
on `PYTHONPATH`, that `result` may be a `dict[str, Workplane]`, what
`--deliver` changes about STL paths, which `cq_verify` helpers exist) are
spread across `prompts/part.md` and `skill/phase3_build.md`.
- mine `error_types` frequencies out of accumulated `build/attempts.jsonl`
  logs and rank them -- interventions must be evidence-led, not guessed
- a short "facts about the run environment" block at the top of
  `prompts/part.md`, one line per counted failure class, replacing scattered
  prose
- check each mined class against `script_lint.py` first: anything the
  linter can catch deterministically should NOT become a prompt line

#### Fold verification into build call
One change -- strategy: reimplement. Chamfer's `execute` auto-echoes
volume/bbox/face count, and `find_holes(part)`/`measure(obj)` are callable
**inside** the sandbox -- so the measured hole inventory comes back with the
build, not from a separate round-trip. On the pulley case that was 4 tool
calls vs Claude Code's 9 turns for the same verified part.
`run_cadquery_model.py` already returns `geometry` this way; the per-part
checks are still separate processes, each paying a fresh OCC import.
- emit the measured interface/feature inventory (what
  `feature_presence_check.py` asserts) inside the wrapper's existing JSON
  contract, as an additive key -- one subprocess produces build + measured
  evidence
- same for `edge_treatment_check.py`'s classify pass where it needs the
  same shape
- keep the standalone CLIs (build-frame reruns, tests); the JSON key is the
  fast path

#### One reconciliation pass
One change -- strategy: reimplement. Their v1 rule: verify with measured
evidence in ONE pass -- check every requested dimension, hole count AND
diameter, feature position **from measured coordinates, not from the
variables you set**, then stop; no further rounds unless a mismatch
appears; never claim correctness while a discrepancy is open. Two findings
behind it: positions were recited from input constants in 21/21 runs
(nothing numeric ever checked them), and open-ended self-verification
bloated cost by 21% with no correctness gain.
- a single-pass reconciliation rule in `skill/phase3_build.md`, explicitly
  bounded ("do not loop extra verification rounds unless a mismatch appears")
- "measured, not recited": a part's self-report must quote wrapper/check
  output, never restate its own `PARAMETERS` block
- "no completion claim while a discrepancy is open" as an explicit gate line

#### Render economy
One change -- strategy: reimplement (scoped). Their F5: 18 mandatory
renders, 5.8s and ~1,150 image tokens each, and **zero** model changes ever
followed one -- the largest clean saving they found. Not transferable
wholesale: our previews also feed user checkpoints and the visual-review
agent, which is a real signal, not a ritual. The rule applies only to
agent-internal self-inspection renders.
- make the autonomous part agent's own re-render conditional: render when
  the part has features a bbox/interface inventory cannot confirm, skip when
  it repeats what the measured checks already proved -- user-facing
  checkpoint renders stay mandatory
- count renders and their token cost per part in the
  [efficiency telemetry](#efficiency-telemetry) first; demote nothing until
  the count is measured here rather than borrowed

#### Output-token economy
One change -- strategy: reimplement. Output tokens are ~46% of cost and
dominate serial decode time; Claude Code's 4.4x output ratio maps almost
directly onto the 3.2x wall-clock gap. Their fix is one prompt line: the
final message is assumptions (if any) + one summary line, no
feature-by-feature recap -- the reconciliation pass already proved the
features.
- bound the per-part completion report in `prompts/part.md` /
  `skill/phase3_build.md` (the recap duplicates the plan and the check
  output)
- measure it as its own change -- it is the one v1-eff ingredient not
  implicated in that arm's correctness regression, but it was never
  measured alone either

#### Assumption pinning
One change -- strategy: reimplement. Zero assumption statements in 21/21
runs, while structurally divergent readings shipped silently (bearing bore
along X in two reps, along Y in the third, same prompt). Their v1 line: if a
dimension or placement is underdetermined, choose the standard engineering
reading and state it in one line before building. This is the same defect
class as the C5 compass-language and reference-frame items at the top of
this file, and it is far cheaper than the elicitation machinery in the
intent-recognition section -- it does not ask the user anything, it just
makes the coin-flip reviewable.
- one-line assumption statement before building, wherever a
  frame/axis/facing/datum is underdetermined -- `prompts/part.md` and the
  Phase 3 correction path
- land it as a `request_log` entry so the assumption survives the session
  (ties into [Typed request_log entries](#typed-request_log-entries) above)

#### Warm kernel process
One change -- strategy: reimplement -- needs measurement first. Chamfer
keeps one MCP server alive per conversation (`lifecycle: "keep-alive"`), so
the kernel is imported once and a failed step is fixed by re-running only
the failing snippet. Every `run_cadquery_model.py` invocation pays a fresh
interpreter + OCC import. Their tool timings put `execute` at 1.3s against
`inspect_part` at 2.1s and `render_view` at 5.8s, so process startup is a
real fraction of tool time, and tool time was ~32% of wall.
- measure first: cold OCC import cost per attempt vs. total attempt wall
  ([efficiency telemetry](#efficiency-telemetry))
- only if it pays: a keep-alive worker that re-executes the whole script in
  a warm interpreter -- NOT incremental session state. A fresh namespace per
  run is a correctness property here (the script file is the deliverable
  and must stand alone); their "re-run only the failing snippet" habit
  trades that away and is not adopted
- the same warm process should serve the trimesh/fcl whole-model checks,
  which pay their own import cost per invocation

#### Context-surface audit
Folds into the [context-creep restructure](#context-creep-restructure)
above. Their 8x context gap came from tool schemas and general scaffolding
read every turn: 6 curated tools and a one-screen system prompt vs 59 tool
schemas. Our analog is not tool schemas but phase documents and reference
files -- `skill/phase3_build.md` alone is ~1,090 lines, and
`reference/scripts.md` indexes ~30 scripts of which any one part uses a
handful. This is evidence for the standing context-creep restructure item,
with a measurement attached rather than a feeling.
- measure context tokens read per phase per part
  ([efficiency telemetry](#efficiency-telemetry)) before choosing between
  the three restructure options already listed under `Tasks for next version`
- per-phase curated script/reference subsets, so a part loop does not carry
  the planning and export surface

#### Eval method held-out set
One change -- strategy: reimplement. Every case in `evals/cases/` is public
and readable during skill iteration, so the scorecard cannot distinguish
"the skill got better" from "the skill got tuned to these cases". Chamfer's
protocol: a public dev set for iteration, a git-ignored private test set
read exactly once after a freeze commit, N=3 repetitions, and the success
bar written down BEFORE tuning (theirs: v1 > v0 on correctness, else >= 25%
cost/latency improvement at equal correctness). They then reported honestly
that v1 met neither bar.
- a git-ignored `evals/private/` test set with the same case schema, never
  read during skill development, run at release freezes
- N repetitions per case with per-case variance in the scorecard -- their
  whole "structural divergence" finding came from comparing reps of one
  prompt
- over-claim as a scored metric: the run claims completion while the
  quality gate has open findings (their `detectOverClaim` is a five-line
  check over the final message plus the grade -- we have both)
- write the pass bar into the release checklist before the tuning round,
  not after

### CadAgent token budget management
CadAgent (github.com/SSSSSia/CadAgent), rated **High** in
`documentation/related_projects.md` -- an LLM-agent-powered FreeCAD
workbench. Its token-budget management tracks how much context an agent
turn is about to consume and trims/summarizes proactively, rather than
reacting after hitting a limit. Directly relevant to this skill's
context-heavy part loop (`prompts/part.md`, `skill/phase3_build.md`) --
overlaps the standing [context creep restructure](#context-creep-restructure)
item. CadAgent's Progressive Context Injection (loading reference/script
content incrementally rather than all at once) is the same idea and should
fold into that restructure decision rather than tracked separately.

### CadAgent smart clarification policy
CadAgent, same row. Instead of always stopping to ask when a parameter is
underspecified, auto-assume a reasonable default and state the assumption,
escalating to a question only past some ambiguity threshold. Overlaps
[Spec audit ambiguity categories](#spec-audit-ambiguity-categories) and
[Assumption pinning](#assumption-pinning) -- CadAgent's contribution is the
policy for WHEN to assume vs. ask, which neither of those items currently
decides.

### CadAgent undo/rollback snapshots
CadAgent, same row. Automatic snapshots before each agent-driven edit,
restorable on request -- a simpler cousin of the checkpoint-branching idea
from ClawSCAD/ClawdCAD (`documentation/related_projects.md` rows). Scope
for this skill: snapshot a part script (and its `BUILD_PLAN.json` entry)
before an LLM-initiated correction round, so a bad autonomous edit can be
reverted without re-running the whole part loop. Lighter-weight than full
branching -- no alternate-timeline UI, just "restore last known-good".

### harnesscad pre-kernel verification
ReverseZoom2151/harnesscad, rated **High**. Verifies CAD operations
symbolically before the kernel runs them -- e.g. catching "fillet radius
exceeds half the smallest extent" from the operation's own parameters,
instead of after OCC throws a boolean-failure error. `script_lint.py` is
AST-level and geometry-unaware (it can't relate a fillet radius to an edge
length without evaluating expressions), so this is a genuine gap between
lint and runtime. harnesscad's "measured gate" (certify only when
independent measurement predicates pass) also matches and could sharpen
`cq_verify.py`'s existing assertions. Cross-checking against 13 independent
kernels is explicitly not worth adopting for a single-kernel skill.
- add named, parameter-level pre-flight predicates (fillet/chamfer radius
  vs. edge length, boss diameter vs. wall thickness, etc.) that run before
  the boolean op itself, not just before the whole script -- `cq_verify.py`
  or a new sibling helper

### Text2CAD MLYengineering repair and learning
MLYengineering/Text2CAD, rated **Medium-High**. A 7-stage
Planner/Implementation/Validation/Repair/Execution/Evaluation/Learning
pipeline over FreeCAD, built on the same "LLMs reason, deterministic tools
decide" philosophy as this skill. Two adoptable refinements to
`quality_gate.py`'s fix loop, which today just re-prompts `claude -p` with
the current error list:
- Repair Agent: rule-bound, non-rewrite patches -- constrain the fix prompt
  to emit a scoped diff/patch against the specific failing construct
  instead of license to rewrite the whole script, cutting regression risk
  from unrelated changes
- Learning Agent: cross-attempt failure aggregation -- feed the fix prompt
  a summary of what already failed on prior attempts for this part (today
  each `claude -p` fix call sees only the current error, not the attempt
  history already sitting in `build/attempts.jsonl`), so repeated fixes
  don't re-try the same wrong correction

### Multi color material support (Claude-To-Print)
OzAILabs/Claude-To-Print, rated **High** -- concretizes the standing bare
`Multi color / material support` item above. A close analog skill (Claude
Code + build123d, same staged design-brief -> parametric-script ->
deterministic-export -> mesh-QA -> visual-feedback pipeline). Concrete
mechanism: multi-color/multi-material 3MF export via `lib3mf`, splitting a
part into named color regions and exporting a pre-colored 3MF for
AMS-style multi-filament printers. `threemf_multi.py` currently tracks
named unions/plates but not per-region color -- that's the gap to close.

### Parameter Sets
e. g. Lego interface definition
unit is "one point" (w * l * h): 8 * 8 * (3 * 3,2) ; center point (r * h): 2,4 * 1.8 , ...
reference:
- https://brickipedia.fandom.com/wiki/LEGO_Brick?file=Brick-in-mm.svg
- https://www.bartneck.de/2019/04/21/lego-brick-dimensions-and-measurements/

### G-code simmulator
Print analysis script (time, weight, slow segments) 

- [ ] Copy `src/print_analysis/` to `cq-design/scripts/` and add a SKILL.md step that runs it after slicing (`python -m print_analysis summary|slow <file.gcode>`)
- [ ] Install `klipper_estimator` (Windows binary) and check the config flag names with `--help` (`--config_file`, `--config_moonraker_url`)
- [ ] Pull limits (accel, velocity) from the U1 Moonraker config and pass them to the estimator
- [ ] Measure the startup offset (PRINT_START, heat-up, homing) on 2-3 real prints and set it as the default `--offset`
- [ ] Compare estimated time and weight with the real print time and spool weight, then adjust density and offset
- [ ] Add G2/G3 arc support in `parser.py` (moves are currently skipped with a warning)
- [ ] Use `klipper_estimator dump-moves` in `slow_segments.py` for the real planned speed (acceleration-limited)
- [ ] Report min-layer-time slowdowns separately from deliberately slow features (bridge, overhang)
- [ ] Set the material per tool (T0-T3) from the U1 spool/RFID data instead of the `--material` flag
- [ ] Test with a real multi-tool U1 G-code (tool changes, prime tower)
- [ ] Optional: expose `mcp_server.py` as an MCP server (`pip install "mcp[cli]"`) and register it in Claude Code

