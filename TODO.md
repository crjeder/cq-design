# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.

- [x] consolidate tasks / ideas from `Block_Sources.md`, `market_research.md`, `occ-error.md`
      and `README.md` into `TODO.md` (here). DONE: README's `Related projects` table moved to
      `info/related_projects.md` (status/relevance column dropped -- that tracking lives here);
      gaps found in `Block_Sources.md` (cq_gears/cqMore/cqterrain, PartCAD) and `occ-error.md`
      (the OCC deepcopy crash) added below as new items. `market_research.md`'s ideas were
      already fully reflected in the "From market research" section further down.
- [x] optimize `CLAUDE.md` it's to heavy
- [x] "write early": cheaper resumption after interrupt (e. g. out "Usage limit reached") --
      shipped via openspec change `add-early-write-journal`: `build/journal.md` append-only
      milestone log + `skill/resume.md` resume procedure; `parameters.py` write moved to the
      Phase 1 dimension checkpoint.
- [x] Improve cross section selection. The renders do not show anything useful.
      User's position (2026-08-11): sections should concentrate on (a) features the
      LLM has clarification questions about, (b) features the human has complained
      about, (c) all other features mentioned in the conversation -- in that priority
      order. DONE via openspec change `improve-cross-section-selection`:
      `skill/phase3_build.md`'s Step 3 `--extra-section` guidance is now an
      unconditional rule (was a skippable judgement call) -- every named+positioned
      `interfaces[]` entry is a cut candidate, ranked into 3 tiers by
      `request_log_search.py <name>` match (clarification > correction > unmatched,
      most-recent-first within a tier via request_log's append-only order), capped at
      3 cuts, axis chosen from the interface's `wall` field (or largest-magnitude
      `position_mm` component as fallback). Bbox-center fallback now only fires when a
      part has zero named+positioned interfaces. Doc/procedure-only change -- no
      schema or renderer code touched (the `--extra-section` plumbing and
      `interfaces[].name` field already shipped). Deliberately deferred to follow-up
      if usage shows a need: a variable (non-fixed-3) cap, and guaranteeing tier-3
      ("everything else") always gets at least one cut slot even when tiers 1-2 alone
      fill the cap. Explored 2026-08-11, findings:
      - The CUTTING machinery is fine; only SELECTION is broken.
        `render_preview._section_cuts` already honors `--extra-section axis=pos`
        (repeatable, and it REPLACES the centerline cuts). The fallback is 3
        bbox-centerline cuts -- on a hollow box, the one place guaranteed to show air.
      - `skill/phase3_build.md:335-345` already tells the author to add
        `--extra-section` per declared position, but as a CONDITIONAL ("if this part
        unions a feature into a body that already has a cavity...") -- a judgement
        call the author skips, so the useless fallback fires. Make it a rule, not a
        condition.
      - The three buckets already exist as `request_log`'s `kind` enum:
        `correction` = (b), `clarification` = (a), `initial`/rest = (c). Chronological
        append-only order gives recency ranking for free; `src/request_log_search.py`
        is the existing keyhole reader.
      - MISSING LINK: `request_log.text` is free prose -- it names no feature and
        carries no coordinate. Nothing turns "the ear standoff sits too low" into
        `y=5`. Needs a name<->position table to join against.
      - BLOCKER RESOLVED via openspec change `add-interface-name-field`: `interfaces[]`
        now declares an optional `name` field (`^[a-z][a-z0-9_]*$`, unique within a
        part), so interfaces that carry both `name` and `position_mm` can exist in a
        schema-valid plan and `skill/phase3_build.md:317-325`'s `--callout` emission can
        fire. The name<->position join this item needs is now available; the join
        itself (below) is not yet implemented.
      - CHEAP VERSION once `name` lands, no new selection logic: sections follow the
        callouts. "Every feature that earns a callout badge earns a cut through its
        `position_mm`; order by `request_log` recency, most recent `correction` first;
        cap at N; centerline cuts only when the list is empty." Text->feature matching
        can be `request_log_search.py <feature_name>` -- the shared-vocabulary change
        exists so the human's wording and the geometry use the same token, so grep is
        a legitimate join.
      - Open questions for whoever picks this up: (1) who selects -- the part author
        passing `--extra-section` (needs a rule it will follow) or `render_preview`
        reading `BUILD_PLAN.json` itself (deterministic, but the tool does not parse
        the plan today); (2) budget -- 3 cuts today, is 6 useful or noise on a part
        with 15 mentioned features; (3) axis choice -- a `position_mm` is a point, not
        a plane, so pick the axis normal to the interface's `wall`, or cut all three;
        (4) explicit tagging (optional `features: [<name>]` on a `request_log` entry,
        exact join, planner must maintain it) vs. grep.
- [x] check if there is a fillets before chamfers rule (improves visual quality) --
      was prematurely marked done against the horizontal/vertical Chamfer/Fillet
      *type* rule below (which treatment to use where, not call order). The actual
      call-order rule (fillet before chamfer in the same chain) shipped via openspec
      change `fillet-before-chamfer-order-check`: `script_lint.py`'s new
      `fillet_after_chamfer` finding.
- [x] optimize prompts, they are growing to long
  - [x] Pass 1 done: `emboss_text.md` (text/emboss gotchas) is now appended to
      `{{CQ_REFERENCE}}` only for parts that involve text (was concatenated into every
      part prompt); removed the duplicate fit-clearance row from the FDM "Basic Dimension
      Rules" table (planning.md rule 4 is the source of truth); verified the coordinate
      tables in planning.md/part.md/SKILL.md are consistent.
  - [x] Pass 2 done: `prompts/planning.md`'s Rules section condensed (openspec change
      `condense-planning-prompt`) -- narrative paragraphs tightened to lead-sentence +
      bullets, the accidental duplicate `request_log` rule (old `14.`/`14.`/`15.`
      collision) merged into one rule 14, provenance renumbered to 15. Rule numbers
      1-13 kept stable since `skill/phase2_planning.md`/`skill/phase3_build.md`
      cross-reference them by number (verified unaffected by grep). Whole-file word
      count 3189 -> 2735 (~14%); behavior unchanged, `test_plan_validate.py` +
      `test_eval_corpus.py` still pass.
- [ ] skill improvements from the C5 Phone-Holder retrospective (read 2026-07-25 from
      `D:\3D Druck\C5 Phone-Holder`; 7 correction rounds, plan/scripts/orientations
      inspected). Each sub-item is independent; pick up separately.
  - [x] plan bloat: `part_notes` doubled as a full round-by-round changelog (the cradle's
        part_notes alone is ~6KB of ROUND 2..7 narrative, largely duplicating
        `request_log` and the scripts' own comments). This feeds straight into the
        "prompts growing too long" problem above, since the plan is injected into part
        prompts. DONE via openspec change `searchable-request-log`: `planning_notes`/
        `part_notes`/generated comments now prescribed as current-state-only (schema
        descriptions, `prompts/planning.md` rule 14, `prompts/part.md`,
        `skill/phase2_planning.md`, `skill/phase3_build.md`); `request_log` is the
        exclusive place for round-by-round history, and superseded content is deleted,
        not annotated "SUPERSEDED by round N below". Also fixed the schema's duplicate
        `request_log` property definition and added `src/request_log_search.py` so
        Phase 3 can search it by keyword/kind instead of re-reading the whole array.
  - [x] kinematics for custom (block-free) hinges. planning_notes documents why the
        `kinematics` schema entry was OMITTED: the axis contract requires a referenced
        block with a `dof`, but this hinge is raw-primitive clevis/tongue geometry, so
        declaring it would force a bogus block reference. Result: rounds 4-7 each
        hand-wrote an ad-hoc boolean fold-collision sweep (0.25deg steps, plus a
        binary search for the minimum notch height Z=16). Two-part fix, proposed as
        openspec changes (2026-07-27):
        (a) DONE via openspec change `blockless-kinematics`: `block` is now optional on
        a `kinematics` entry (a block-less entry declares `axis_origin_mm`/`axis_dir`/
        `type`/`required_range`/`step` directly, with an optional `mechanical_limit`
        for the numeric check, reported as `range_check_not_applicable` when absent
        rather than silently skipped), and `plan_validate.py`'s joint-contract arms
        (type match, axis parallelism, coaxiality) are skipped for it since there is no
        block to contract against.
        (b) DONE via openspec change `contact-limited-sweep`: `interference.py` now uses
        fcl only as a broadphase and measures overlap as `manifold3d` boolean
        intersection *volume* (the measure the hand-written sweeps used and got right);
        `stop_on_contact` marks a joint whose travel ends against another body, so first
        contact is reported as its mechanical stop (`contact_limited_stop` warning with
        the achieved range) instead of a `motion_collision`. Implementing it surfaced a
        third defect the proposal had missed: the sweep walked `required_range` lo->hi,
        so a fold declared `[-90, 0]` started at -90 -- maximum interpenetration, a pose
        reachable only through the joint's own stop -- and reported that first sample as
        the stop. Fixed by travelling OUTWARD from the authored zero (`travel_arms`),
        splitting a straddling range into two independent arms. Verified against the C5
        Phone-Holder cradle/plate hinge: stop reported at -54.0deg (true first contact
        -53.5deg, offset by the 0.1mm^3 tolerance) with min clearance 0.2mm, the designed
        value -- previously a range-wide 5557mm^3 collision error on a part that folds
        cleanly in the hand.
  - [ ] STILL OPEN from the original ad-hoc sweeps: the minimal-cutout search ("how tall
        must the notch be to clear this swing?"), which the phone-holder session answered
        by hand with a binary search over geometry edits. That is a search loop over
        edits, not a measurement change -- its own change if wanted.
  - [x] hinge design-rule reference: rounds 5-6 were both instances of one geometric
        rule the LLM got wrong twice and the user derived: for a flat face to fold
        flush against a target plane at exactly +-90deg, the pivot axis must stand off
        the folding face's plane by exactly the axis's perpendicular distance to the
        target plane (here EAR_STANDOFF = PIVOT_Y = 5mm; rotation-matrix proof in
        `cradle.py`). Add a "flush-fold hinge placement" recipe (with that derivation
        and the clevis/tongue/standoff vocabulary) to `reference/` so the part prompt
        can get it right the first time instead of via user correction.
  - [x] orientation cache staleness: `build/orientations.json` still carries the
        round-4 rationale and `build_height_mm: 8.599` for the cradle, whose round-6
        geometry is 16.1mm tall -- `build.py` "reuses orientations.json when present"
        with no invalidation, so deliverables regenerate against stale orientation
        data/scores after geometry edits. Add invalidation: store a hash of the part
        script (or the geometry bbox) alongside each entry and recompute (or at least
        warn) on mismatch. Fixed by the `build-artifact-freshness` change:
        `src/freshness.py` stamps a part script's hash on the orientation result and
        on the export manifest; `build_template.resolve_orientations` recomputes a
        stale entry instead of reusing it, and the kinematic/plate-clearance/keep-out
        stages flag a stale exported STL as `stale_artifact` instead of validating
        superseded geometry.
  - [ ] print-orientation bed-stability term: cradle part_notes records that BOTH
        `strength` and `min_support` modes picked a pose balanced on a single
        0.635mm^2 contact point (would tip instantly); the user had to override to
        visual_quality + show_face to get the sane flat pose. Scoring weighs overhang
        only, not bed-contact stability. Add a bed-contact-area / tipping term (or a
        minimum-contact floor) to `print_orientation.py` scoring. Cross-ref: memory
        `skill_gap_print_orientation_pathological_poses`, and the Tweaker-3
        reimplementation block below (Tweaker's bottom-contact formulas cover this).
  - [ ] telemetry not written in real runs: `build/attempts.jsonl` is absent from this
        7-round project, so the eval harness's first-shot-rate / attempts-to-pass /
        cost metrics have no data from exactly the kind of session they exist to
        measure. Verify SKILL.md phase 3 actually prescribes the `telemetry.py append`
        call per attempt (and per correction round), and make the quality gate warn
        when the file is missing/empty at delivery.
  - [ ] formalize the `parameters.py` sourced-measurements convention: the project
        grew an ad-hoc root-level `parameters.py` ("sourced real-world measurements...
        not imported by the build") that keeps user-measured numbers + provenance +
        correction history separate from each script's resolved PARAMETERS block.
        It proved valuable across rounds (hole 60->55 correction etc.) but is pure
        convention: nothing generates, validates, or reconciles it. Decide: make it a
        prescribed Phase 1/4 deliverable (dimension research output lands there), and
        optionally extend `import_params.py` beyond the w/d/h mapping so edits stay
        reconciled with the plan.
  - [ ] prescribe the printable-foundation authoring frame up front: the plate script's
        Z_OFFSET pattern (author the part with its physical bottom at script Z=0, then
        undo via `placement.translate_mm` to land in the shared assembled frame) was
        "discovered/adopted during the build" per planning_notes. It is a good general
        pattern for parts whose assembled frame has the part floating (here bottom at
        Z=-2). Add it to the part prompt / phase-3 guidance as the default convention
        instead of leaving each session to rediscover it.
  - [ ] correction rounds driven by user sketches: rounds 5-7 were steered by annotated
        images (`ear-placement.png`, `hinge-ear.png`, `C5 Aschenbecher-annotated.jpg`)
        that the session preserved in the project root and referenced from
        request_log/part_notes ad hoc. Formalize: request_log entries get an optional
        `images` field, sketches are copied into the project (e.g. `sketches/`), and
        the part prompt is told to re-read the referenced sketch when iterating on
        that feature.
- [x] engineering rationale in part scripts -- `openspec/changes/engineering-knowledge/`
      sections 1-3 done (2026-07-27): `prompts/part.md` now requires an
      `ENGINEERING RATIONALE` comment block between PARAMETERS and MODEL (full
      three-line form -- load path, worst-case stress location, a check computed from
      the script's own parameter names against a stated allowable -- for parts with a
      declared `load` or a load-bearing `blocks_needed`/archetype; one-line form
      otherwise), backed by a new `reference/Engineering Design Rules.md` (material
      constants, snap-fit strain formula, rib/boss/gusset ratios) wired into Phase 3's
      substitution table, plus new "Engineering rows" in
      `reference/Visual Review Checklist.md`. Section 4 (eval-corpus A/B run,
      `IMPROVEMENT_PLAN.md` update) still open. `eval-geometric-part-matching`
      (2026-07-29) fixed the scorer's part-correspondence bug so an A/B is finally
      trustworthy, but the three run directories on disk (`baseline-pre-claude5`,
      `before-citation`, `after-citation`) are not that A/B -- `before-citation`/
      `after-citation` predate these hooks entirely (item 13's citation change,
      2026-07-20/21) and `baseline-pre-claude5` is a pre-Claude-5-migration
      baseline. Section 4 still needs a fresh hooks-on-vs-off run pair; see
      `openspec/changes/eval-geometric-part-matching/proposal.md`'s "Re-score
      Results" section for the re-scored numbers and this caveat in full.
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
- [ ] add textures capability https://github.com/Stone-Age-Sculptor/StoneAgeLib/blob/main/images/DemonstrationTexture.png
- [x] add a 90 deg dove tail joint. and a generalization: the angle is a parameter
- [ ] feature: reverse engineer 3D mesh / point cloud into primitives. 
      (-> Differential geometry comparison) / "import" mesh files (.stl) 
- [ ] capability to import (and integrate) B-Rep files (.step. / stp, fcstd, .brep, .iges)
- [x] design error: the llm often places the center of a box where actually a one of the walls  should sit --
      INTRA-PART case DONE via openspec change `intra-part-mating-area` (`verify_backed`
      in `cq_verify.py`: a feature's face, named by a signed axis, must be fully backed
      by a named neighboring feature -- bbox reach + orthogonal-axis containment).
      Reproduces and fixes the C5 Phone-Holder hinge-knuckle standoff bug
      **TEST** works in that case, but faces do not need to be always fully backed, only if it's the designers intention
      (`build/cradle.py` ROUND 5-7 comments: a standoff centered on the pivot coordinate
      was only half-backed by its leg, which stopped exactly at that coordinate instead
      of the standoff's far edge). Vocabulary ("mating area", "backed by material")
      reused from `openspec/changes/archive/2026-07-01-joint-contract/design.md:412-421`.
      INTER-UNION case NOT implemented -- that archived design covers a block declaring a
      mating area between the two unions of a multi-body block (e.g. a hinge's two
      leaves), checked once at the whole-model gate after export. It was captured only as
      "exploratory capture, NOT ready to implement" and stayed blocked on two open cruxes
      that `intra-part-mating-area` does not touch: (1) satisfaction algebra -- precisely
      how a requested joint matches a block instance (axis-alignment semantics, range
      subset, how plan A/B bind to the block's two unions); (2) sub-body naming
      convention -- how a multi-union block labels its sub-bodies so `model_export` splits
      them into distinct unions instead of fusing them into one compound. Both need their
      own exploration before that half can be built.
      OPEN CRUX for whoever picks up that archived design next: does `verify_backed`
      generalize upward into the inter-union check once those cruxes resolve (applied to
      two unions' exported STLs instead of two in-script solids), or does it stay a
      separate, narrower mechanism that only shares vocabulary with the block-level one?
- [x] BuildPlan is very verbose (pose prose in `planning_notes`) -- DONE via the
      `author-owned-placement` change (`openspec/changes/author-owned-placement/`):
      the planner declares `pose_intent` (one line, human-readable) instead of
      authoring `placement`; `placement` is now the part author's write-back. See
      that change's design.md D1-D6 for the alternatives considered (a transform
      matrix, deriving everything through `joints`) and why they were rejected.
- [x] pose-intent field: DONE via `author-owned-placement` (see above) -- `pose_intent`
      is a per-part optional string (`src/build_plan_schema.json`), planner-written
      (`prompts/planning.md` rule 8), author-consumed (`prompts/part.md`
      `{{POSE_INTENT}}` + contract rule 6), with the transform written back into
      `placement` after the part is accepted (`skill/phase3_build.md` "Placement
      write-back"). Open questions from this item's exploration were resolved: intent
      gets its own field (not folded into `description`), and the authoring frame is
      per-part, chosen freely by the author (design D2's plan-level-convention
      alternative was rejected as premature).
- [ ] rationale audit: decide what `planning_notes` is FOR, then bound it.
      User's position (2026-08-11): keep it as durable design rationale IF that helps
      a re-plan; the scratchpad role is dropped. (An earlier session recommended the
      scratchpad, reasoning that the model's working-out had nowhere to live between
      turns -- extended thinking is that scratchpad now, and it is correctly
      turn-local. Persisting turn-local reasoning into the artifact is what makes the
      field unbounded, since nothing can ever be deleted if nothing knew its purpose.)
      "Helps re-plan" is a hypothesis, not an observed need: a re-plan agent today
      reads `request_log` (via the keyhole `src/request_log_search.py`) and `parts[]`,
      and never opens `planning_notes`. THE TEST: take a real correction round from
      HitsterTower or the C5 Phone-Holder and ask what the re-planner would have got
      wrong without `planning_notes` that `request_log` + `parts[]` did not already
      give it. Nothing -> the field is dead weight and the pose-intent item above
      replaces rather than reforms it. Something -> that list IS the field's schema,
      and everything outside it gets banned by a rule in `prompts/planning.md`.
      Precedent for the "keep it but bound it" outcome: `request_log` is the other
      unbounded append-only prose field, and it was solved not by compressing the text
      but by giving it a reader that never loads it whole (`request_log_search.py`,
      `skill/phase3_build.md:26-28`). Copy that shape, not a new compact schema.
      Likely survivor regardless of the verdict: rule 15's provenance (source URL,
      license, sourcing rung) is a legal record rather than reasoning, so it may want
      out of free text into a structured field entirely.
      Cheap independent win, available before the audit resolves: one rule in
      `prompts/planning.md` banning prose restatement of `placement` -- the structured
      field is the single source. Pure deletion, no schema change, and it kills the
      bulk of the HitsterTower example above on its own. DONE via `author-owned-placement`
      (`prompts/planning.md` rule 8a).
      LLM answer:
      "Concrete gaps, not just "less context":

      **1. Wall adjacency would silently break.** The user's original sketch was a↔c, c↔d, d↔b, b↔a. `request_log` never records that this doesn't close (74.3/74.3/61.4/67.8 don't form a rectangle under that pairing). `parts[]` only shows the *result* (interfaces named `corner_d_a_tails`, `corner_a_c_pins`, etc.) with no signal that this ring order differs from what was asked. A re-planner reading only those two would either reproduce the user's literal (non-closing) adjacency, or re-derive *some* closing order — possibly a different one than a↔c, c↔b, b↔d, d↔a — and never know it needs to justify the deviation to the user. Only `planning_notes`' PLAN NORMALIZATION section says this explicitly.

      **2. It would re-attempt rejected archetypes.** `parts[]` records what was built (scratch geometry), not what was tried and discarded. Nothing in `request_log` mentions `stand` or `plate-boss-pattern`. Without the ARCHETYPES REJECTED note, a re-planner doing archetype matching on wall_d (has a "boss") or base (has "bosses"/pockets) would re-evaluate those same archetypes from scratch — possibly picking one this time, since it has no memory of *why* they were rejected (wrong shape family, not a parameter tweak).

      **3. It would likely add a `joints` array and fail validation.** Four parts each declare a `dovetail_corner` interface — exactly the shape of a matched-pair block the schema wants in a top-level `joints` entry. A re-planner pattern-matching on `parts[]` alone has strong reason to add one. It would then hit the tree-topology constraint (4-cycle, no valid `root_part`) as a validation error with no explanation of why — instead of knowing upfront, as `planning_notes` states, that this is structurally impossible here and the mating is deliberately expressed via `interfaces` + placement instead.

      **4. It wouldn't know the base's sourcing question was already resolved.** Phase 0 triage (search for a reusable existing model before designing from scratch) isn't recorded anywhere in `parts[]`, and `request_log`'s initial entry only says STLs were measured for reference. Without the SOURCE note ("from-scratch rebuild, no third-party model found or reused, no web lookup needed"), a re-planner would either redo that search or not know it's allowed to skip it.

      **5. The authoring-frame convention would need re-deriving per part instead of once.** Each wall's own `part_notes` states its own placement, but not *why* all four share the same flat-authored convention (origin on the west corner, dovetail run in the build plane). That reasoning — tied to a block requirement (tooth-tiling axis must lie in the build plane) — lives only in WALL AUTHORING FRAME / PLACEMENT. A re-planner regenerating one wall in isolation, from that wall's `part_notes` alone, has no cross-part signal that deviating breaks the corner-joint printability property, not just that wall's own printability.

      Everything else in `planning_notes` (DFM cleanup summary, orientation policy rationale) is largely restated per-part in `part_notes`, so it's redundant there — the five above are the ones that are genuinely load-bearing only in `planning_notes`."
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

