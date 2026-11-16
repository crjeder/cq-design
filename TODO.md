# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.

Each item is a one-line pointer. Rationale, investigation notes and strategy
discussion live in `documentation/todo-*.md`, linked from the item. Closed
investigations are in [documentation/todo-case-history.md](documentation/todo-case-history.md).
Completed tasks are in [documentation/DONE.md](documentation/DONE.md).

Items are clustered by theme, not by where the idea came from (survey, comparison,
session). Clusters are sorted by rating, best first. A cluster's rating is the best
rating among its items: an explicit rating from the related-project survey
([documentation/related_projects.md](documentation/related_projects.md)) where one
exists, else the stated impact or gain, else a judgement call (noted in the cluster).
Ties are ordered by the best-ranked item. Items inside a cluster are ordered the same way.

# V1.1.0
V1.0 is released.

## 1. Pipeline enforcement and process hygiene
Rating: **High** (build123d-mcp comparison ranked the state machine #1 by impact; the open defect is the same idea).

- [ ] Process hygiene: every test file reached by CI, flaky tests fixed or deleted never retried, no one-off helper scripts in `src/` -- [details](documentation/todo-pipeline.md#process-hygiene-and-install-checks)
- [ ] `/retrofit` for projects already in flight: run the absence lints, report what the plan/scripts lack, offer to add the missing `coordinate_frame` / `joints` / `verify_*` before a correction round -- [details](documentation/todo-case-history.md#c5-fixes-did-not-take-2026-09-08)

## 2. Evals, telemetry and failure mining
Rating: **Medium-High** (Top-10 survey items 1, 4, 10; item 1 produces the evidence the others need).

- [ ] Per-attempt efficiency telemetry: wall time, cold OCC import and per-tool time in `attempts.jsonl` / `tool_calls.jsonl`, shown in the eval scorecard -- [details](documentation/todo-evals-telemetry.md#per-attempt-efficiency-telemetry)
- [ ] Failure-mode mining: `log.py attempt stats`, then a "Run environment facts" block (or lint rule) per counted failure class -- [details](documentation/todo-evals-telemetry.md#failure-mode-mining)
- [ ] Under-specified eval cases, scored on `asked_when_needed` / `asked_when_not` (gates assumption pinning and the assume-vs-ask policy) -- [details](documentation/todo-evals-telemetry.md#under-specified-eval-cases)
- [ ] Test cases: Salacia case, [SUP Silencer](https://makerworld.com/de/models/2871437-paddleboard-sup-deflation-silencer#profileId-3205902), beamer-halter -- [details](documentation/todo-evals-telemetry.md#test-cases-to-add)

## 3. Quality gates and conformance checks
Rating: **Medium-High** (Top-10 items 3, 7, 9; build123d-mcp item 2; text-to-cad gate ideas).

- [ ] Plan conformance gate: check each part against its `BUILD_PLAN.json` entry by measurement, plus a +-10% parameter-perturbation robustness audit -- [details](documentation/todo-quality-gates.md#plan-conformance-gate)
- [ ] Scoped repair patches + attempt history in the `quality_gate` fix loop (reject rewrites above a changed-lines cap) -- [details](documentation/todo-quality-gates.md#scoped-repair-patches-and-attempt-history)
- [ ] Differential geometry vs the previous attempt (`geometry_regression` warnings from `build/baseline/`) -- [details](documentation/todo-quality-gates.md#differential-geometry-vs-the-previous-attempt)
- [ ] Per-project `design_rules.json` + gate stage that fails with the rule's own id -- [details](documentation/todo-quality-gates.md#per-project-design-rule-file)
- [ ] Gates: tri-state result (pass / fail / unverified); a check that could not run must never read as a pass -- [details](documentation/todo-quality-gates.md#gate-ideas-from-the-text-to-cad-survey)
- [ ] Gate findings: facts vs verdicts; each finding cites the limit's source and the JSON path of the measurement -- [details](documentation/todo-quality-gates.md#gate-ideas-from-the-text-to-cad-survey)
- [ ] `thin_regions`: report `min_mm` and `p05_mm`, violation = `p05` below the limit -- [details](documentation/todo-quality-gates.md#gate-ideas-from-the-text-to-cad-survey)
- [ ] Unit-scale sanity flag (`units_suspect`) in the gate / `measure_stl.py` -- [details](documentation/todo-quality-gates.md#gate-ideas-from-the-text-to-cad-survey)
- [ ] `script_lint.py`: reproducibility rules for part scripts (no time, randomness, env vars, working directory, own outputs) -- [details](documentation/todo-quality-gates.md#gate-ideas-from-the-text-to-cad-survey)
- [ ] DFM numbers in `reference/`: record rule provenance; an unverifiable rule is reported as missing, never a silent default -- [details](documentation/todo-quality-gates.md#gate-ideas-from-the-text-to-cad-survey)
- [ ] Hole checks against the solid geometry (cylindrical faces of the CadQuery solid), never passing an ambiguous match -- [details](documentation/todo-quality-gates.md#hole-checks-and-hole-advisories)
- [ ] Change rules into advisories: make holes drop shaped, "hole found" -- [details](documentation/todo-quality-gates.md#hole-checks-and-hole-advisories)

## 4. Intent, assumptions and clarification
Rating: **Medium-High** (Top-10 items 5, 6; intent-recognition survey).

- [ ] Assumption pinning: emit `ASSUMPTION:` lines, record them as `request_log` kind `assumption`, ask only when readings cannot both be satisfied -- [details](documentation/todo-intent.md#assumption-pinning)
- [ ] One measured reconciliation pass: quote every requested dimension from tool output, never from script variables -- [details](documentation/todo-intent.md#one-measured-reconciliation-pass)
- [ ] Intent as invariant, remaining: model-level conformance bar before delivery, promote request-conformance findings to blocking (eval-gated), `REQUIREMENTS.md` is read by no gate -- [details](documentation/todo-intent.md#intent-as-invariant)
- [ ] Ask whether equal-valued parameters are one parameter or independent (three holes of 5 mm; a rectangle with equal sides) -- [details](documentation/todo-case-history.md#c5-knuckle-pivot-ping-pong)
- [ ] Generate testable statements from user intent (different agent than the planner) -- [details](documentation/todo-intent.md#fixed-geometry-and-testable-statements)
- [ ] Distinguish geometry that is fixed from geometry the skill may change any time, e. g. during optimization -- [details](documentation/todo-intent.md#fixed-geometry-and-testable-statements)
- [ ] Read back parameters on any user-initiated planning/authoring round

## 5. Context, cost and performance
Rating: **Medium** (build123d-mcp item 3 and the optimisation gains; ranked by stated gain).

- [ ] Restructure to combat context creep -- [details](documentation/todo-context-cost.md#context-creep-restructure)
- [ ] Warm kernel worker: keep CadQuery/OCC loaded across part-loop attempts, crash-contained; measure the cold-start share first -- [details](documentation/todo-context-cost.md#warm-kernel-worker)
- [ ] `kinematic_check.py` sweep: load/build once, set the fcl transform instead of copying, decimate or bbox-gate the boolean. Gain: high on plans with joints -- [details](documentation/todo-context-cost.md#optimisation-backlog)
- [ ] Tessellate once for STL + 3MF, coarser tolerance for analysis STLs. Gain: medium -- [details](documentation/todo-context-cost.md#optimisation-backlog)
- [ ] `preview.py`: vectorized shading, tessellate once. Gain: medium -- [details](documentation/todo-context-cost.md#optimisation-backlog)
- [ ] "Activate" all necessary knowledge domains in the LLM (audit says mostly done; close at the next pass) -- [details](documentation/todo-context-cost.md#knowledge-domain-activation-audit)

## 6. Preview and visual review
Rating: **Medium** (judgement: the open `every named feature is shown` defect and blank cross-sections both trace here).

- [ ] Phase 3: mandatory visual self-review after any geometry change; builder picks extra views that show the edited feature (`section_select.py` is a start) -- [details](documentation/todo-preview.md#preview-ideas)
- [ ] Draw feature edges on preview renders (lower value, worth a look) -- [details](documentation/todo-preview.md#preview-ideas)
- [ ] Face labels / stable references drawn on the preview PNG so a user can point at a feature -- [details](documentation/todo-preview.md#preview-ideas)

## 7. Joints, kinematics and anchors
Rating: **Low-Medium** (judgement: no rated source; all are extensions of working checks).

- [ ] Kinematic: ground/seating-plane check (lid-hits-floor) -- [details](documentation/todo-joints.md#kinematic-ground-plane)
- [ ] Kinematic: articulated chains (a moving union carries other unions through the sweep) -- [details](documentation/todo-joints.md#kinematic-articulated-chains)
- [ ] Joints: multi-DOF / coupled simultaneous movements -- [details](documentation/todo-joints.md#joints-multi-dof)
- [ ] Blocks: assembly placeholder / keep-clear-for-assembly geometry (the `support_cost` half of the clearance-opening suppression is still open) -- [details](documentation/todo-joints.md#blocks-assembly-placeholder)
- [ ] Joints: side-tagged `face_mount` docks for automatic union membership/axis derivation -- [details](documentation/todo-joints.md#face-mount-docks)
- [ ] Anchors: BOSL2-style attachment helper for intra-part feature placement -- [details](documentation/todo-joints.md#bosl2-style-anchors)
- [ ] HitsterTower: dovetail-corner-joint form outside the single-rooted joints tree (resolved by `rigid-joint-loops`; migrating the tower is a follow-up eval case) -- [details](documentation/todo-joints.md#hitstertower-dovetail-form)

## 8. Parametric sources and block library
Rating: **Low-Medium** (`fetch_step.py` is stated low priority; the rest are unrated).

- [ ] "Parameter sets": critical dimensions only (gridfinity, gravitrax, Lego); the LLM designs freely within them -- [details](documentation/todo-sources.md#parameter-sets)
- [ ] Generic parametric SCAD importer -> build blocks on the fly
- [ ] Search tool for specific parametric cadquery / SCAD / build123d models
- [ ] `src/fetch_step.py`: query the step.parts API and download verified STEP to `build/refs/` -- [details](documentation/todo-sources.md#step-fetch-script)
- [ ] Custom support, see https://github.com/gittrahan/support-fins
- [ ] PCB clip generator: combine standoffs and clip heads instead of screws
- [ ] Tool to create enclosures (all major maker boards, cutouts for widely used connectors)
- [ ] Tool to produce cable traces where cables are held press fit

## 9. FEM and print analysis
Rating: **Low-Medium** (judgement: `fem_check.py` is a screening tool; the gaps matter only if asked to do more).

- [ ] `fem_check.py`: solve orthotropic instead of isotropic -- [details](documentation/todo-simulation.md#fem-checker-follow-ups)
- [ ] `fem_check.py`: source E/nu/allowable from measured filament data -- [details](documentation/todo-simulation.md#fem-checker-follow-ups)
- [ ] `fem_check.py`: real contact/fastener patch boundary conditions instead of a footprint-radius node selection -- [details](documentation/todo-simulation.md#fem-checker-follow-ups)
- [ ] fem: calculate required wall thickness, global then regional -- [details](documentation/todo-simulation.md#fem-checker-follow-ups)
- [ ] fem: more infill only for compression load; infill direction = load direction -- [details](documentation/todo-simulation.md#fem-checker-follow-ups)
- [ ] G-code analysis script (time, weight, slow segments): integrate `print_analysis` into the skill and calibrate on real prints -- [details](documentation/todo-simulation.md#g-code-simmulator)

## 10. Import, export and materials
Rating: **Low** (judgement: no rated source; each depends on slicer or format decisions).

- [ ] Export: 3MF print-plate structure (slicer-specific extension) -- [details](documentation/todo-import-export.md#export-print-plate-structure)
- [ ] Reverse-engineer a 3D mesh / point cloud into primitives; import STL -- [details](documentation/todo-import-export.md#reverse-engineer-mesh)
- [ ] Import/integrate B-Rep files (STEP/STP, FCStd, BRep, IGES)
- [ ] Engineering of multi-material interfaces and properties; still open: multi-material FEM, per-union density within one part -- [details](documentation/todo-import-export.md#multi-material-and-slicer-parameters)
- [x] Calculate and export slicer parameters (wall loops, infill, support, brim) -- layer height and infill exported via `--formats estampo`; walls/support/brim remain -- [details](documentation/todo-import-export.md#multi-material-and-slicer-parameters)
- [ ] Add textures capability
- [ ] Accept Markdown / formatted UTF-8 text input

## Related ideas
Surveyed projects, ratings and open ideas live in [documentation/related_projects.md](documentation/related_projects.md).
