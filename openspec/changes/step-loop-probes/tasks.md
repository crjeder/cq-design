## 1. Spike: probes against the eval failures

- [x] 1.1 For the 4 eval parts that failed `visual_mismatch` (`adapter-ring`, `boss-plate`, `east-side-mount`, `two-part-box`), hand-write the plan-derived probes `probes.py plan` would seed and run them on the rejected scripts
- [x] 1.2 Record per part whether the probes pass the geometry the auditor rejected and whether they catch any real defect; write the result to `openspec/changes/step-loop-probes/spike.md` and stop for review if probes would not have settled at least 3 of the 4

## 2. Probes and the Part recorder (eager mode)

- [x] 2.0 Plan schema: `blocks_needed[]` objects gain `id`, `params`, `edges`; `plan.py validate` checks each instance's `params` and `edges` against its inventory entry; tests for the three planning-phase scenarios
- [x] 2.1 `src/probes.py`: probe kinds `solid_at`, `empty_at`, `ray`, `bbox`, `delta` evaluated on BRep (point classification, line intersection), plus the face-distance placement helper
- [x] 2.2 `src/probes.py`: registry with owner (plan or step index), transform on place, retirement by a later step's tool envelope for block-owned probes only
- [x] 2.3 `src/probes.py plan`: seed step-0 probes from a plan part entry (`solids == 1`, envelope bbox, interface-type table for `interfaces[]` with `position_mm`), reporting `unprobed_interfaces`
- [x] 2.4 `Part` recorder in `src/blocks/` with `select(name, id)`, plan-bound `resize(handle)`, `param(id, name)`, `positions(id)`, `place` (`at` point or list, `rotate`, `op` base/union/cut, `into` for unions), `result()`; plan lookup via `CQ_PLAN` or walking up from the script; eager execution with per-step checks
- [x] 2.5 Tests: probe kinds on known solids, registry transform and retirement, plan probe seeding, select/resize errors (missing instance, unknown/missing param), plan edit changes geometry with the script unchanged, eager `Part` result equals the equivalent hand-built Workplane
- [x] 2.6 `plan.py import-params`: `not_applicable` for step scripts; test

## 3. Primitives and block probes

- [x] 3.1 Primitive entries `box`, `cylinder`, `cone`, `sphere`, `prism`, `revolve` with probe functions
- [x] 3.2 Probe function for every block in `src/blocks/` (fasteners, connectors, joints, hardware, gridfinity, primitives)
- [x] 3.3 Edge sets: every entry declares `edge_sets` with local-frame curves; remove cosmetic edge options from blocks (`fillet_box` `corner_r` becomes `box` + plan `edges`), keeping functional radii as block params
- [x] 3.4 Inventory schema: `kind`, required `probes` and `edge_sets`; update `inventory.json` for blocks, primitives and templates
- [x] 3.5 Test: every inventory entry has a probe function and its probes pass on its default build; every declared edge set yields at least one curve on the default build

## 4. Templates in step form

- [x] 4.1 Convert every `templates/*.py` to a select/resize/place step list with no dimension literals; each template entry's probes cover every feature it builds
- [x] 4.2 Update `templates/archetypes.json` and its schema for the step form, including the plan instance `params`/`edges` each archetype needs
- [x] 4.3 Test: each converted template builds the same volume and bbox as before conversion (within tolerance)

## 5. Lint allowlist

- [x] 5.1 `script_lint.py`: `raw_cadquery` error for any CadQuery call or `Workplane` method in a part script, with a hint naming the closest primitive; `script_dimension` error for a `PARAMETERS` block or any argument to `resize`
- [x] 5.2 Tests: raw extrude rejected, `PARAMETERS` and `resize` args rejected, position arithmetic and loops accepted, converted templates lint clean

## 5b. Edge treatments in the finishing pass

- [x] 5b.1 `Part.result()` under `CQ_PRINT_ROTATE`: map each instance's declared edge sets to final-body edges lying on the placed curves, chamfer horizontal / fillet vertical and diagonal edges in print pose, untreated when the variable is unset
- [x] 5b.2 Re-check plan probes after treatment, retire block probes inside treated zones, raise typed `finishing_probe_failed` (action `ask_user`) on a failing plan probe or an unmapped edge set; surface it from `write_assembly.py`
- [x] 5b.3 `export_standalone.py` and `bundle_project.py` ship `BUILD_PLAN.json` next to the scripts so plan-bound `resize` resolves in the deliverable
- [x] 5b.4 Tests: rotated-pose box chamfers its build-pose vertical edges, step loop untreated, chamfer breaking a plan bore probe, lost edge set, standalone export builds

## 6. Step worker

- [x] 6.1 `src/step_worker.py` server: stdlib `multiprocessing.connection` on 127.0.0.1 with authkey, address in `build/.step_worker.json`, idle timeout
- [x] 6.2 Prefix-hash cache (kind, resolved args, entry source hash), executing from the first miss
- [x] 6.3 Client `run <script>`: report contract (`steps`, `failed_step`, `diff_vs_last_good`, `probe_stuck`, `worker`), stop at first failing step, full tier via `run_cadquery_model.py` only when all steps pass
- [x] 6.4 Crash/timeout handling: kill the worker, cold subprocess fallback with the same report, `worker: "fallback"`
- [x] 6.5 Snapshots: `last_good`, `snapshot save|restore|compare`, BRep + source + registry under `build/snapshots/<part>/`
- [x] 6.6 Probe failure history in `build/<part>.steps.jsonl` and the `probe_stuck` rule
- [x] 6.7 Tests: cache reuse after editing step 5, parameter edit invalidation, stop at first failure, later step breaking a plan probe, restore rewrites the script, stuck vs not-stuck, fallback after a forced worker exit

## 7. Telemetry

- [x] 7.1 `log.py` / `run_cadquery_model.py --attempts-log`: attempt number = plan revision count for the part, `step_runs` field
- [x] 7.2 Update eval scorecard attempt counting in `evals/` to the new meaning
- [x] 7.3 Tests for attempt numbering across a plan change and for `step_runs`

## 8. Prompts and orchestration

- [x] 8.0 `prompts/planning.md`: planner emits every instance with `id`, `params` and cosmetic `edges`; parameter-level corrections edit the plan, not scripts
- [x] 8.1 `prompts/part.md`: step-form authoring, primitives, no raw CadQuery; drop the scratch `verify_stage` construction-plan guidance
- [x] 8.2 `prompts/builder.md`: loop on `step_worker.py run`, fix the failing step or restore a snapshot, return `blocked` on `probe_stuck` or `missing_block`; remove the 3-runs-per-stage budget; return contract carries the last step report
- [x] 8.3 `render_prompt.py audit` + `prompts/audit.md`: drop connectedness and probed-interface questions when a passing step report is present; keep `unprobed_interfaces`
- [x] 8.4 `skill/phase3_build.md`: escalation on `probe_stuck`/`missing_block` with plan change as an option; plan change logs to `request_log` and starts a new attempt
- [x] 8.5 `reference/scripts.md` and `FILES.md` entries for `probes.py`, `step_worker.py`, the `Part` API and the changed lint/telemetry contracts

## 9. Verification

- [ ] 9.1 Regenerate eval part scripts and run the eval suite
- [ ] 9.2 Compare `visual_mismatch` rate, blocked rate and attempts per part against the 2026-09 baseline; record in `spike.md`
- [ ] 9.3 `uv run pytest tests/`, `ruff check`, `ruff format`
