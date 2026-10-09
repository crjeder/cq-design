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

## Backlog

### Geometry / Blocks / Tools

- [ ] custom  support https://github.com/gittrahan/support-fins
- [ ] "parameter sets" not a full tool, but critical dimensions. LLM freely designs but gets a few constraints (e. g. gridfinity, gravitrax, lgego) (details)[#parameter-
- [ ] PCB Clip generator. instead of using screws to hold to PCBs in place comine standoffs and clip heads.
- [ ] Tool to create enclosures (for all major maker boards and cutouts for all widely used connectors
- [ ] tool to produce cable traces where cables are held press fit for 

### Skill improvement

- [ ] generic parametric SCAD importer -> build blocks on the fly
- [ ] search tool for specific parametric cadquery / SCAD / build123d modells
- [ ] optimisation: https://github.com/yeicor-3d/dl4to4ocp
- [ ] Restructure to combat context creep -- [details](#context-creep-restructure)
- [ ] "Activate" all necessary knowledge domains in the LLM -- [details](#knowledge-domain-activation-audit)

### Kinematic, Joints and Simulation

- [ ] Kinematic: ground/seating-plane check (lid-hits-floor) -- [details](#kinematic-ground-plane)
- [ ] Kinematic: articulated chains (a moving union carries other unions through the sweep) -- [details](#kinematic-articulated-chains)
- [ ] Joints: multi-DOF / coupled simultaneous movements -- [details](#joints-multi-dof)
- [ ] Blocks: assembly placeholder / keep-clear-for-assembly geometry -- [details](#blocks-assembly-placeholder)
- [ ] Joints: side-tagged `face_mount` docks for automatic union membership/axis derivation -- [details](#face-mount-docks)
- [ ] Anchors: BOSL2-style attachment helper for intra-part feature placement -- [details](#bosl2-style-anchors)
- [ ] HitsterTower: dovetail-corner-joint disassembly form fell outside the joints schema's single-rooted tree -- [details](#hitstertower-dovetail-form)
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
- [ ] Preview: z-buffered renderer (removes painter's-algorithm shading artifacts) -- [details](#preview-z-buffered-renderer)
- [ ] Preview: render feature-detail previews more proactively -- [details](#preview-proactive-detail-renders)
- [ ] Reverse-engineer a 3D mesh / point cloud into primitives; import STL -- [details](#reverse-engineer-mesh)
- [ ] Import/integrate B-Rep files (STEP/STP, FCStd, BRep, IGES)
- [ ] Read back parameters on any user-initiated planning/authoring round

### Orthers

- [ ] cover more of the workflow (slicing, parameters, print)
- [ ] Accept Markdown / formatted UTF-8 text input
- [ ] Add textures capability
- [ ] Multi color / material support -- [details](#multi-color-material-support-claude-to-print)
- [ ] Engineering of multi-material interfaces and properties
- [ ] calculate and export slicer parameters such as: wall loops, infill, support, brim (auto brim in orca is terrible)

### Optimisation

- [ ] 3. `quality_gate.py` runs once per union and re-runs the whole-model stages (kinematic, plate clearance, keep-out) each time, reloading every STL. Fix: run them once per model, or cache on manifest + plan hash. Gain: high on multi-part plans
- [ ] 4. `kinematic_check.py` sweep: per-pose `mesh.copy()` + `apply_transform`, full-resolution manifold booleans, 8 bisect steps x azimuths, STL reload and `CollisionManager` rebuild per entry. Fix: load/build once, set the fcl transform instead of copying, decimate or bbox-gate the boolean. Gain: high on plans with joints
- [ ] 7. Repeated tessellation per union (3MF at 0.01, STL, shim default, preview per view) and a 0.01 mesh feeding all trimesh analysis. Fix: tessellate once for STL + 3MF, coarser tolerance (~0.02-0.05) for analysis STLs. Gain: medium, compounds with 1, 4, 5, 6
- [ ] 9. `preview.py`: per-triangle Python shading, per-triangle `verts[list(f)]`, re-tessellation per panel/section. Fix: vectorized `np.cross` shading, `verts[faces]`, tessellate once. Gain: medium

### Top 10 ideas from the related-project survey

Ranked by value/cost out of the open ideas in
[documentation/related_projects.md](documentation/related_projects.md) (rating
column + "Open ideas" list). Each item is written to be implementable without
re-reading the survey; the background lives in that file's Details section.
Order matters: 1 produces the evidence 4 needs, 2 and 3 cut fix-loop failures,
5 and 6 are prompt-only. Every item: one openspec change, one runnable test.

- [ ] **1. Per-attempt efficiency telemetry** (source: SmartAI/Chamfer, rated Medium-High)
  - Why: `build/attempts.jsonl` (`src/log.py`, `validate_attempt`) holds only
    `part_id, attempt, outcome, error_types, prompt_chars, model, visual_review, ts`.
    `src/session_cost.py` already gives billed cost per *session* (`build/cost.json`);
    nothing says where wall-clock or tool time goes per attempt or per tool.
  - Do: (a) `log.record_attempt` accepts and stores optional `wall_ms` (time around the
    `run_cadquery_model.py` subprocess; the wrapper's `--attempts-log` path is the
    reliable source because the PostToolUse hook does not see sub-agent calls, see the
    `hooks skip sub-agent tool calls` memory) and `cadquery_import_ms` (cold OCC import,
    measured in `run_model_shim.py`). (b) `render_preview.py` and the check CLIs append
    `{tool, part_id, ms, payload_bytes}` to `build/tool_calls.jsonl`. (c) Keep every new
    field OPTIONAL in `validate_attempt`; old logs must stay valid. (d)
    `evals/run_evals.py` `attempt_metrics` adds `mean_wall_s_per_attempt`, per-tool
    totals and render count, shown in `render_markdown`; `n/a` when absent.
  - Test: `tests/test_log.py` (old record validates, new optional fields validate, bad
    type rejected) and `tests/test_run_evals.py` (metrics with and without the fields).
  - Done when: a scorecard row shows wall time and render count, and a log written
    before this change still scores.

- [ ] **2. Pre-kernel parameter predicates** (source: harnesscad, rated High)
  - Why: `script_lint.py` is AST-only (cannot relate a fillet radius to an edge length)
    and `cq_verify.py` fires after the boolean. A bad fillet/chamfer reaches OCC and
    returns `Standard_ConstructionError`/`StdFail_NotDone`, a vague error.
  - Do: add `check_fillet(body, radius, selector=None, label="")`,
    `check_chamfer(...)` and `check_ligament(wall_mm, hole_d_mm, min_mm, label="")` to
    `src/cq_verify.py`. They measure the selected edges/faces with CadQuery and raise
    the module's marked `RuntimeError` (`_fail(kind, label, detail)`) with new kinds
    `fillet_radius`, `chamfer_size`, `thin_ligament`. Use the radius-vs-edge rule that
    `prompts/part.md` already states in its fillet/chamfer safety line; do not invent a
    new threshold. Register the kinds in `_VERIFY_HINTS` in `src/run_cadquery_model.py`
    (that dict is what turns a marker into a typed error with a hint). Document the
    helpers in the "Construction-time verification" section of `prompts/part.md`.
  - Test: `tests/test_cq_verify.py`: radius too large raises with the kind and label;
    valid radius returns the body unchanged; `tests/test_run_wrapper.py`: marker maps to
    the typed error.
  - Done when: an over-large fillet in a fixture script yields `errors[0].type ==
    "fillet_radius"` with a hint, not an OCC exception.

- [ ] **3. Scoped repair patches + attempt history in the fix loop** (source: MLYengineering/Text2CAD, rated Medium-High)
  - Why: `quality_gate._render_fix_prompt` asks `claude -p` to output the whole script
    and `run_gate` overwrites `script_path` with it (`MAX_FIX_ROUNDS = 2`). Nothing
    limits unrelated rewrites, and round 2 does not know round 1's fix failed.
  - Do: (a) in `run_gate`, keep the pre-fix text, compute `difflib.unified_diff` after
    `_extract_python`; if more than `FIX_MAX_CHANGED_FRACTION` (start 0.3) of lines
    changed, restore the original and report a `fix_rejected` info issue. (b) keep a
    `history` list across rounds (issue `type`s, and the changed hunks capped at 40
    lines); `_render_fix_prompt(script_path, issues, history)` adds a "Previous fix
    attempts that did not resolve these issues" block, and an instruction to change
    only the failing construct. (c) also append the part's earlier `error_types` from
    `attempts.jsonl` (`log._read_records` + `fold_attempts`).
  - Test: `tests/test_quality_gate.py` with `_call_claude` monkeypatched: a full rewrite
    is rejected and the file restored; round-2 prompt contains round-1 history; a small
    patch is accepted.
  - Done when: a deliberately over-eager fake fixer cannot change more than the cap.

- [ ] **4. Failure-mode mining -> run-environment facts block** (source: SmartAI/Chamfer, rated Medium-High)
  - Why: Chamfer killed 11 of 15 failed tool calls with four sentences of environment
    facts, each traced to a counted failure. Our equivalent facts are scattered over
    `prompts/part.md` and `skill/phase3_build.md`. Needs item 1's data or the existing
    `error_types` field.
  - Do: (a) new `python src/log.py attempt stats <attempts.jsonl> [--top N]` printing
    `error_types` frequency over `fold_attempts` records, and the types that occur on
    a failed attempt immediately followed by a pass. Also usable on eval run dirs
    (`evals/run_evals.py` `read_attempts`). (b) For each type with >= 3 occurrences in
    >= 2 parts: if `script_lint.py` can catch it deterministically, add a lint rule
    instead; otherwise add ONE line to a new "Run environment facts" block placed
    before "### Contract rules" in `prompts/part.md`, with the count and date in a
    comment. (c) Assert in `tests/test_render_prompt.py` that the block renders.
  - Done when: `attempt stats` runs on a real `attempts.jsonl`, and each fact line
    traces to a counted class.

- [ ] **5. Assumption pinning** (source: SmartAI/Chamfer, CadAgent smart clarification policy)
  - Why: structurally different readings of one prompt (bearing bore along X vs Y)
    shipped silently with zero assumption statements; same defect class as the
    compass-language and shared-pivot items. Cheaper than asking the user.
  - Do: (a) `prompts/part.md` and `prompts/builder.md` (Return contract): when a
    frame, axis, facing, datum or direction is underdetermined, choose the standard
    engineering reading and emit `ASSUMPTION: <one line>` before building; list them in
    the return contract. (b) `src/build_plan_schema.json`: add `"assumption"` to the
    `request_log` `kind` enum (currently `initial | clarification | correction`);
    `skill/phase3_build.md` records each via `log.py request add --kind assumption`.
    (c) `plan_validate`'s intent-reconciliation check (`check_intent_reconciled`) must
    NOT treat `assumption` as a user clarification/correction that stales `intent`;
    add that exclusion. (d) Escalation rule from CadAgent: ask the user only when two
    readings differ in a way the part cannot be built to satisfy both.
  - Test: `tests/test_plan.py` (schema accepts `assumption`, reconciliation ignores it)
    and `tests/test_log.py` (`request add --kind assumption`).
  - Done when: an eval case with an ambiguous axis shows the assumption in
    `request_log` and the audit can cite it.

- [ ] **6. One measured reconciliation pass** (source: SmartAI/Chamfer, rated Medium-High)
  - Why: positions were recited from input constants in 21/21 Chamfer runs; open-ended
    self-verification added 21% cost without correctness. Our parts self-report from
    their own `PARAMETERS` block.
  - Do: `skill/phase3_build.md` and `prompts/part.md`: replace free-form verification
    with ONE pass: for every requested dimension, hole count and diameter, and
    `interfaces[]` position, quote the value from tool output
    (`run_cadquery_model.py` `geometry`, `feature_presence_check.py`, `measure_stl.py`),
    never from the script's variables; stop unless a mismatch appears; no completion
    claim while a discrepancy is open. Also bound the per-part completion report to
    assumptions plus one summary line (output-token economy). Pairs with item 5.
  - Test: `tests/test_render_prompt.py` asserts the rule text is in the rendered
    builder prompt; add one eval case whose request has a numeric position the author
    could mis-recite.
  - Done when: the rendered prompts carry the rule and the eval case passes.

- [ ] **7. Differential geometry vs the previous attempt** (source: vericontext/cadgate, rated Medium-High)
  - Why: `quality_gate.py` judges each attempt alone, so a regression between
    attempts (volume halves, bbox shifts, wall thins) is invisible.
  - Do: after each successful wrapper run store `build/baseline/<part_id>.json` =
    `{volume_mm3, bbox_mm, min_wall_mm (if --wall-min), face_count}` from the
    wrapper's `geometry` block. New gate stage `_run_regression_stage` compares the
    current run to it and emits `geometry_regression` warnings above thresholds
    (volume +-25%, bbox axis +-20%) unless the latest `request_log` entry targets
    that part with `level` `functional` or `operation` (an intended change). Update
    the baseline on gate pass. `--no-baseline` flag to skip. Advisory, never blocks.
  - Test: `tests/test_quality_gate.py`: unchanged part passes; halved volume warns;
    warning suppressed when a targeted correction exists.
  - Done when: editing a part to remove a large feature produces one warning naming
    the old and new volume.

- [ ] **8. Multi-color / multi-material 3MF export** (source: OzAILabs/Claude-To-Print, rated High; backlog item "Multi color / material support")
  - Why: `exporters/threemf_multi.py` writes one named object per union plus Bambu/Orca
    plate metadata (`_model_settings_config`), but no per-object color or filament.
  - Do: (a) schema: optional `color` (`#RRGGBB`) and `filament` (1-based slot) on a
    part and on a `unions[]` entry (resolution like `units.plate_of`: union, then
    part, else none). (b) `write_named_3mf` takes an optional per-object
    `{color, filament}`; write `<basematerials>` + `pid`/`pindex` in
    `3D/3dmodel.model` for the color and the slicer's extruder metadata in
    `Metadata/model_settings.config`. Verify the exact Bambu/Orca key names against
    BambuStudio's `bbs_3mf.cpp` first, as the existing plate code did; do not guess
    them. (c) `deliverables._write_3mf` passes the values; `plan.py summary` shows a
    color column; `prompts/planning.md` rule: split by union, one color per union (a
    color boundary inside one solid is out of scope). (d) STL/STEP exports unchanged.
  - Test: `tests/test_assembly_and_deliverables.py`: two unions with different filament
    produce two distinct extruder entries; zero-color plan output is byte-identical to
    today's.
  - Done when: a two-color fixture opens in OrcaSlicer with two filaments assigned
    (manual check, noted in the change).

- [ ] **9. Per-project design-rule file + assertions** (source: cad-khana / FreeCAD-AI, rated Medium-High)
  - Why: DFM limits live in `plan.constraints` and `profile.json`; there is no way to
    say "all edges >= 0.8 mm fillet, min wall 1.2 mm for this project" and have the
    gate fail on it with the rule's own text.
  - Do: optional `design_rules.json` at the project root, a list of
    `{id, check: "min_wall" | "min_fillet" | "min_clearance" | "max_overhang", value,
    scope: "all" | [part ids], severity}`. `init_permissions.py` does not seed it.
    New `quality_gate._run_design_rules_stage` maps each rule onto data the gate
    already computes (`thin_regions` for wall, `edge_treatment_check` for fillet,
    `plate_clearance_check`/`keep_out_check` for clearance, `_analyze_stl` for
    overhang) and re-labels the finding with the rule `id`. Add a JSON Schema
    `src/design_rules_schema.json` validated by `plan.py validate`-style call. No new
    geometry code.
  - Test: `tests/test_quality_gate.py`: a rule tighter than the plan default fails a
    fixture part; a missing file adds no issue.
  - Done when: a project rule of 1.2 mm min wall blocks a 1.0 mm wall with a message
    naming the rule id.

- [ ] **10. Under-specified eval cases (and the assume-vs-ask policy they gate)** (source: ProCAD, CadAgent; intent-recognition item 5)
  - Why: every case in `evals/cases/` is well specified, so no elicitation or
    assumption change can regress and the scorecard cannot see it. It is the gate on
    items 5 and 6 and on `spec audit` work.
  - Do: (a) 4 new cases under `evals/cases/` whose `request.md` omits one named
    category each (missing dimension, conflicting constraint, unstated frame, unstated
    fit/load), plus 2 well-specified controls; `case.json` gets
    `expect: {"ask": true|false, "category": "..."}`. (b) `run_evals.py` scores
    `asked_when_needed` and `asked_when_not` from the run's `request_log`
    `clarification` entries (and `assumption` entries once item 5 lands), reported
    separately so asking about everything cannot win. (c) `tests/test_eval_corpus.py`
    validates the new `expect` block; `tests/test_run_evals.py` scores a fixture run.
  - Done when: the scorecard prints both rates and a control case that triggers a
    question lowers `asked_when_not`.

## Related ideas
Surveyed projects, ratings, open ideas and their background live in [documentation/related_projects.md](documentation/related_projects.md). The ten most valuable open ideas are the "Top 10" items above.

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
GPL-incompatible, see [Integration strategies](documentation/related_projects.md#integration-strategies)).

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
([Canonical intent restatement](documentation/related_projects.md#canonical-intent-restatement)), which shipped
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
restatement](documentation/related_projects.md#canonical-intent-restatement) and `openspec/changes/
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
entries](documentation/related_projects.md#typed-request_log-entries), [Request-relative
acceptance](documentation/related_projects.md#request-relative-acceptance)) -- the generation loop's output is now
checked against `intent`/`request_log`, not only against the plan's structure.

What is still open, narrowly:
- (closed by `openspec/changes/parameter-entry-routing-check/`: a `parameter`-level
  entry appended with `--snapshot-scripts` is diffed by `quality_gate.py`, which warns
  `routing_violation` on an untargeted, non-joint-linked script change -- advisory
  only, so it does not yet stop the C5 sibling-literal edit, only surfaces it);
- promotion of advisory request-conformance findings to blocking-by-default is
  still eval-gated and undone (item 5, [Under-specified eval
  cases](documentation/related_projects.md#under-specified-eval-cases));
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
[harnesscad pre-kernel verification](documentation/related_projects.md#harnesscad-pre-kernel-verification); no
new item needed.

The doc's "Domain-Specific NLP" row (intent disambiguation, hierarchical
decomposition) is the one domain NOT covered by reference-file injection --
Phase 1's topology clarification is narrow (shape ambiguity only). This is
already the subject of a full separate survey; see
[Intent-recognition survey](documentation/related_projects.md#intent-recognition-survey) for the five-item
breakdown (typed `request_log`, ambiguity-category audit, request-relative
acceptance, canonical intent restatement, under-specified eval cases) -- no
new item needed here either.

Net: this bullet is closer to DONE than open. What's actually left under it
collapses into the two already-tracked items above; keeping it as a
separate top-level bullet risks double-tracking the same gap under three
names. Recommend closing this bullet at the next TODO pass and letting the
two linked items carry the remaining work.

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

