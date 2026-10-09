# Completed tasks for V1.0

- [x] OCC deepcopy crash on print-orientation rotation -- fixed via openspec changes
      `bypass-cq-warehouse-copy-patch` (`src/cq_compat.py` restores native `Shape.copy`) and
      `fix-orientation-bintools-deepcopy` (`placement.apply_cq` uses `BRepBuilderAPI_Transform`);
      specs `shape-transform-safety` and `model-export`. Known gap: a part script importing
      `cq_warehouse` directly (bypassing `blocks.hardware`) re-installs the patch.
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
  - [x] the minimal-cutout search ("how must the notch be to clear this swing?"), which 
        the phone-holder session answered
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
  - [x] print-orientation bed-stability term: cradle part_notes records that BOTH
        `strength` and `min_support` modes picked a pose balanced on a single
        0.635mm^2 contact point (would tip instantly); the user had to override to
        visual_quality + show_face to get the sane flat pose. Scoring weighs overhang
        only, not bed-contact stability. Add a bed-contact-area / tipping term (or a
        minimum-contact floor) to `print_orientation.py` scoring. Cross-ref: memory
        `skill_gap_print_orientation_pathological_poses`, and the Tweaker-3
        reimplementation block below (Tweaker's bottom-contact formulas cover this).
  - [x] telemetry not written in real runs: `build/attempts.jsonl` is absent from this
        7-round project, so the eval harness's first-shot-rate / attempts-to-pass /
        cost metrics have no data from exactly the kind of session they exist to
        measure. Verified `skill/phase3_build.md` Step 5 already prescribes the
        `telemetry.py append` call per attempt (and per correction round) unambiguously
        -- the prescription was not the gap. Shipped: `quality_gate.py` gained a
        telemetry-presence stage that warns (never blocks) when `attempts.jsonl` is
        missing/empty/unparseable, reported at delivery in `skill/phase4_deliver.md`.
  - [x] formalize the `parameters.py` sourced-measurements convention: the project
  - [x] formalize the `parameters.py` sourced-measurements convention: the project
        grew an ad-hoc root-level `parameters.py` ("sourced real-world measurements...
        not imported by the build") that keeps user-measured numbers + provenance +
        correction history separate from each script's resolved PARAMETERS block.
        It proved valuable across rounds (hole 60->55 correction etc.) but was pure
        convention: nothing generated, validated, or reconciled it. The
        prescribed-deliverable half was already done by `add-early-write-journal`
        (`skill/phase1_requirements.md` writes it at the Phase 1 checkpoint,
        `skill/phase2_planning.md` updates it in Phase 2, `dimension-validation-checkpoint`
        spec covers the procedure). DONE via openspec change
        `formalize-parameters-sourcing`: closed the remaining verification gap with an
        advisory `parameters_missing` quality-gate stage (warns when
        `build/journal.md` records the `phase1/dimensions_approved` milestone but
        `parameters.py` is missing/empty), surfaced at Phase 4 delivery. Extending
        `import_params.py` beyond the w/d/h mapping to reconcile `parameters.py` edits
        was explicitly decided against -- the two files hold different kinds of values
        (raw sourced measurements vs. resolved/derived geometry) with no observed case
        of them drifting in a way that mattered; see that change's design.md Non-Goals.
  - [x] prescribe the printable-foundation authoring frame up front: the plate script's
        Z_OFFSET pattern (author the part with its physical bottom at script Z=0, then
        undo via `placement.translate_mm` to land in the shared assembled frame) was
        "discovered/adopted during the build" per planning_notes. It is a good general
        pattern for parts whose assembled frame has the part floating (here bottom at
        Z=-2). Add it to the part prompt / phase-3 guidance as the default convention
        instead of leaving each session to rediscover it.
  - [x] correction rounds driven by user sketches: rounds 5-7 were steered by annotated
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
- [x] rationale audit: decide what `planning_notes` is FOR, then bound it. DONE via
      openspec change `bound-planning-notes`: bounded to three categories (decisions
      against something, cross-part invariants, assembly procedure/hardware), a
      general no-prose-restatement rule, and a re-plan read-before-rewrite clause.
      Post-V1.0 follow-ups filed and left open: provenance move to a structured field
      (rule 15), structured `{considered, rejected_because}` entries for category (a),
      and the bill of non-printed materials (TODO.md item above).
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
- [x] `interface` third type: `union` (fused into the parent part's body, distinct from
      mating docks like `face_mount` and kinematic axes like `hinge_axis`) -- DONE.
- [x] `hinge_axis` interface type is too narrow: generalize the kinematic-axis vocabulary
      (revolute/prismatic/spherical) rather than the single `hinge_axis` token -- DONE
      (replaced by motion-agnostic `joint_axis`).
- [x] preview: cross-section previews wired into workflow. The `--cross-sections`
      flag now renders a 3x3 grid (6 exterior + 3 interior section views) as the
      default for whole-part validation. Visual Review Checklist extended with
      items 8-10 (hollow/wall integrity, internal features, unintended voids) to
      exploit the interior views. (DONE: PR #39).
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
- [x] add a 90 deg dove tail joint. and a generalization: the angle is a parameter
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
- [x] `cq_warehouse` (gumyr/cq_warehouse, 151 stars) -- strategy: pinned dep --
      already the project's `cq-warehouse` git dependency. No action.
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

## Closed at V1.0 release (from TODO.md)

- [x] Implement typed `request_log` entries -- [details](related_projects.md#typed-request_log-entries)
- [x] Compass-language mixup in orientation reasoning -- FIXED 2026-09-11: `coordinate_frame` schema field + `plan_validate.check_coordinate_frame_usage` advisory -- [details](../TODO.md#c5-compass-language)
- [x] Hinge ear: primitive placed center-aligned to another part's edge -- FIXED 2026-09-11: `quality_gate._run_hinge_guard_stage` flags a hinge-associated union missing `verify_seated`/`verify_backed`/`pin_hinge` -- [details](../TODO.md#c5-hinge-ear-center-vs-edge)
- [x] Cradle knuckle Z ping-ponged because a shared pivot literal was hand-duplicated across part scripts -- FIXED 2026-09-11: `check_shared_interfaces` broadened to flag coincident unnamed interfaces (positional match), plus `check_hinge_intent_without_joints` -- [details](../TODO.md#c5-knuckle-pivot-ping-pong)
- [x] Quality-gate overhang check judged the authored-frame STL, not the print pose -- false-positive `overhang_exceeded` whenever the optimizer rotates the part -- FIXED 2026-09-08 -- [details](../TODO.md#c5-quality-gate-overhang-authored-frame)
- [x] LLM claimed "no support needed" despite a nonzero support score -- FIXED 2026-09-15: `print_recipe.supports` was hardcoded `False`; now derived from any non-advisory `overhang_exceeded` finding -- [details](../TODO.md#silica-tray-support-claim)
- [x] Re-derived print orientation/export after a hand-edit -- correct by design or coincidence? -- ANSWERED + FIXED 2026-09-15: it was coincidence (no rule required it); `skill/phase3_build.md` now has a "Post-delivery corrections" section requiring re-orientation/export/gate before re-reporting delivery -- [details](../TODO.md#silica-tray-re-export-coincidence)
- [x] Missed the intent of the bottom finger-access opening; over-supported the south wall -- FIXED 2026-09-15: `clearance_opening` interfaces now suppress the overhang finding over the declared void -- [details](../TODO.md#hitstertower-oversupport)
- [x] split `info` directory
- [x] Consolidate scattered ENGINEERING RATIONALE into `BUILD_PLAN.json` -- DONE: rationale now lives in `parts[].engineering_rationale`, written back in Phase 3 and checked by `plan_validate.py --require-rationale` (`openspec/changes/archive/2026-09-08-consolidate-engineering-rationale/`) -- [details](../TODO.md#engineering-rationale-consolidation)
- [x] sbom: add credit for projects where code came from -- DONE: `documentation/SBOM.md`, linked from `README.md`
- [x] Intent-based prompt reformulation -- DONE: `BUILD_PLAN.json`'s `intent` is the user-approved reformulation written at the Phase 1 exit checkpoint (`openspec/changes/approved-intent-reformulation/`) -- [details](../TODO.md#intent-based-prompt-reformulation)
- [x] Export a project-regeneration prompt for a fresh LLM session -- DONE: `src/regen_prompt.py` writes `REGENERATE.md` at Phase 4 delivery -- [details](../TODO.md#project-regeneration-prompt)
- [x] Tool to create gridfinity objects -- DONE: `src/blocks/gridfinity.py` (bins, baseplates, feet, socket cutters), `templates/gridfinity_{bin,baseplate}.py`, `src/gridfinity_check.py` (conformance check, auto-scoped quality-gate stage), `reference/gridfinity.md`
- [x] Intent-based prompt reformulation -- DONE, merged into item 4 below and shipped
      as `REQUIREMENTS.md` -- [details](../TODO.md#intent-based-prompt-reformulation)
- [x] Gear geometry (lwidm/cq_gears) -- DONE -- [details](related_projects.md#gear-geometry)
- [x] `cq-gridfinity` -- DONE (reimplemented as `blocks/gridfinity.py`; see the gridfinity tool item above) -- [details](related_projects.md#cq-gridfinity)
- [x] BRep-vs-CSG mindset + selector cheat sheet + anti-patterns + grep-friendly local doc snapshot -- DONE -- [details](related_projects.md#cadquery-authoring-guidance)
- [x] DeepCAD Chamfer-distance golden-mesh regression metric -- DONE -- [details](related_projects.md#chamfer-distance-metric)
- [x] Text-to-CadQuery corpus import (arXiv 2505.06507) -- importer landed, `evals/import_external_corpus.py` -- [details](related_projects.md#text-to-cadquery-corpus)
- [x] WKJBryan/cadquery-library import -- importer landed, `evals/import_external_corpus.py` -- [details](related_projects.md#wkjbryancadquery-library)
- [x] 4. Canonical intent restatement artifact -- DONE, shipped ahead of the freeze
      status below as `REQUIREMENTS.md` -- [details](related_projects.md#canonical-intent-restatement)
- [x] code quality audit

## Closed in V1.1.0 (from TODO.md)

- [x] Katzenwendeltreppe
- [x] bridges are treated as overhangs -> ignore bridges of lengt l (l: printer parameter) -- `constraints.bridge_max_mm`, supported on >= 2 sides
- [x] arc fillets do not produce the intended result -- root-caused: not tessellation (folds survive 75x finer meshing) but hand-built tangent spandrel/prism fillets whose zero-thickness cusp runs past a tapered, chamfered rib; detected by the `sliver_fin` gate finding (`sliver-fin-detection` change). Remedy for authors: end the fillet where the wall is deeper than the fillet plus chamfers, or use `.edges(...).fillet()`
- [x] teardrop shaped holes not used -- `teardrop-hole-enforcement` change (prompt rule, `peak` param, lint + gate hint)
- [x] cross section selection tool. important features should show up in the cross section
- [x] evaluate [CQ-Kit](https://github.com/michaelgale/cq-kit) -- **REJECTED** (no reusable gap: exporters/ already covers STEP/IGES/STL/3MF/OBJ/SCAD, no history of boolean-fuse failures here so fuzzy booleans solve a problem we don't have, and selectors/XSection/Ribbon don't map to blocks/'s interface-aware primitive library; stale API surface too)
- [x] evaluate bernhard-42/jupyter-cadquery **REJECTED** -> not relevant
- [x] evaluate cq's assembly system and https://github.com/bernhard-42/cadquery-massembly -- **REJECTED** (already covered by `placement.py` / `mate_chain.py`); one optional spin-off: assembled multi-component STEP export -- [details](../TODO.md#cq-assembly-and-massembly)
- [x] show differences: https://github.com/bdlucas1/diff3d -- `src/diff_models.py` (boolean diff, JSON + PNG; no alignment, no diff3d dependency)
- [x] for selectors: evaluate https://github.com/voneiden/cq-filter and https://github.com/jmwright/selector_synthesis -- **REJECTED** (cq-filter's filter/sort/[] are native since CQ 2.4 and already in reference/; its only extras, group/last, need a Workplane subclass for little gain; selector_synthesis is a GUI click-to-selector research stub, and there is no picking step here)
- [x] Deduplicate pairwise-mirrored parts into one script/STL -- `copy_of` on a part (`dedupe-identical-parts` change) -- [details](../TODO.md#mirrored-parts-dedup)
- [x] A minimal deliverable for a parametric part -- `src/export_standalone.py` -> `standalone/` (`minimal-part-deliverable` change)
- [x] integrate a FEM-simulation for strength optimisation -- `src/fem_check.py` (`fem-stress-advisor`
      change): advisory only (never gates, never gets a quality_gate.py stage -- BC quality
      doesn't earn that yet), replaces `src/FEM.py`'s bounding-box-guessed stub
- [x] Export: automated 2D plate packing / bed nesting -- **REJECTED** (belongs in a slicer) -- [details](../TODO.md#export-plate-nesting)
- [x] Bill of non-printed materials (BOM: screws, inserts, magnets, pins, adhesives) -- [details](../TODO.md#bill-of-non-printed-materials)
- [x] since orca slicer now supports STEP default to export this format
- [x] optimization for print speed
- [x] User intent as an invariant over generation loops -- DONE (capture via
      `REQUIREMENTS.md`/`intent`, `intent`/`request_log` kept in sync by the `intent_ts`
      reconciliation gate, and every review now checks its render against `intent`/
      `request_log` as a second bar). The `parameter`-level routing rule is now a gate
      warning (`parameter-entry-routing-check`); remaining gaps in [details](../TODO.md#intent-as-invariant)
- [x] 1. `measure_stl.py` `_thin_regions`: up to 3000 brute-force ray-vs-all-triangles casts in a Python loop, per union per wrapper run. Fix: batched `trimesh.ray` (embree/rtree) or chunked rays plus a bbox prefilter. Gain: very high
- [x] 2. Part script runs ~6x per gate (shim, `--deliver`, edge-treatment, feature-presence, toolpath-speed x2, Gridfinity) plus extra Python/`import cadquery` startups. Fix: memoize `_load_result` per (path, hash, rotate), merge the edge-treatment and feature-presence hooks into one load, let `--deliver` reuse the shim result. Gain: high
- [x] 5. `print_orientation.py` candidate loop (~0.5 s/candidate; 205 candidates = 107 s of a 129 s build). Topology caches and near-duplicate normal merging (5 deg) are already done, so the cost is per-pose. Profile: `_is_bridge` 52 s (about 754 regions/candidate; only ~10% pass the 80 deg gate but they pay a qhull `ConvexHull` with a `mkstemp` per call plus two `np.unique`, one with `axis=0`); `triangles_center`/`triangles.mean` recomputed per pose 3x/candidate, ~20 s plus a 6.5 s `triangles` gather (also behind `bed_contact_mask`, 17 s); `_overhang_angles` 4.6 s; `_build_height` 5.8 s. Fix: (a) base-mesh centroids once, per-pose centroid z = `centroids @ R[2] + tz`, shared by `bed_contact_mask` and `_is_bridge`; build the adjacency `keys`/`pairs` once per mesh, not per candidate; (b) in `_is_bridge`, gate all regions at once with `bincount` over component labels and loop only over survivors; replace `np.unique(edges, axis=0)` with 1-D edge keys; skip qhull for tiny regions (closed-form or numpy rectangle); (c) only if the profile shows support cost dominating and `_select` is monotone in it, prune candidates with a lower bound (true cost >= `BRIDGE_COST_FACTOR` x no-bridge cost). Before (b): histogram region face counts and line-profile one candidate. Gain: high (done in 2026-10-08-speed-up-print-orientation-candidates: all of (a), and (b) except the tiny-region qhull skip; (c) candidate pruning deferred, revisit only if a profile shows support cost still dominates)
- [x] 6. `mesh_io.py` `_is_bridge`: Python dict of every edge plus per-edge Python loop per region, run in the gate and per orientation candidate. Fix: vectorize with sorted edge keys + `searchsorted` and numpy masks. Gain: medium-high (done in 522504b; remaining per-region overhead is tracked in item 5)
- [x] 8. `exporters/threemf_multi.py`: pure-Python `_weld`, one `ET.SubElement` per vertex/triangle, zip re-parsed for the manifold count. Fix: `np.unique` weld, join f-strings for XML, count from in-memory arrays. Gain: medium on large models
- [x] 10. Python-loop mesh helpers: `measure_stl._union_find`, `print_orientation._area_cumulation_normals`, `measure_stl._flat_faces`. Fix: `scipy.sparse.csgraph.connected_components`, `np.unique` + `np.add.at`, sorted-z `searchsorted`. Gain: medium, low effort
- [x] progressive overhang penalty (severity exponent `OV_H`)
- [x] `FIRST_LAY_H` band for bottom-contact (replaces tight `CONTACT_Z_EPS_MM`)
- [x] Print-friendly parameterizations: teardrop/bridged holes (Gridfinity) -- `teardrop-hole-enforcement` + `two-pass-print-finishing` (teardrops follow the accepted print pose) -- [details](related_projects.md#print-friendly-parameterizations)
- [x] 1. Typed `request_log` entries (`level` + `targets`) -- DONE, `openspec/changes/
      archive/2026-09-01-typed-request-log/` -- [details](related_projects.md#typed-request_log-entries)
- [x] 3. Request-relative acceptance in the implementation audit -- DONE, `openspec/
      changes/archive/2026-09-01-request-relative-acceptance/` -- [details](related_projects.md#request-relative-acceptance)
- [x] Preview: z-buffered renderer -- numpy rasterizer `src/zbuffer.py` replaced the matplotlib mplot3d path (openspec change `optional-z-buffer-renderer`); no OpenGL.
