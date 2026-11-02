## Why

Builders fail late and noisily. In the 15 eval runs (42 attempts, 12 parts) 7 of 9
failures are `visual_mismatch`, and every one is the auditor trying to confirm a
measurable fact from pictures ("single connected body", "through-hole continues through
the plate") and failing because no section crossed the right plane. The kernel answers
those facts exactly in milliseconds. Meanwhile each validate run costs ~15 s (two cold
CadQuery imports, the script run twice, full mesh checks and a render) and checks only
that the whole script ran, so a defect introduced by one operation surfaces after the
whole part is built, and fixes are stacked on possibly wrong state.

A "fail early, fail often" loop fixes the quality problem: the part is built as a list
of small steps, each step is checked against declared intent (probes) the moment it
runs, every earlier probe is re-checked after every later step, and the builder iterates
freely on geometry while only plan changes cost an attempt.

## What Changes

- **BREAKING** Part scripts become an ordered list of step calls. A step is exactly one
  of `select` (choose a block, template or primitive), `resize` (bind its parameters)
  or `place` (transform it and add or cut it against the host body). Raw fluent
  CadQuery is no longer allowed in part scripts; geometry not covered by a block is
  built from primitives. The script stays the single source of truth and the
  deliverable (`build.py`, gate and `CQ_PRINT_ROTATE` reloads run it unchanged).
- **BREAKING** `resize` takes no values: it binds the instance's `params` from
  `BUILD_PLAN.json` (`blocks_needed[]` gains `id`, `params`, `edges`). Part scripts carry
  no dimension literals and no `PARAMETERS` block, so a dimension change is always a
  plan edit.
- **BREAKING** Cosmetic edge treatments leave the build loop: they are plan-declared
  per instance edge set and applied in the existing print-pose finishing pass, chamfer
  or fillet chosen per edge from its print-pose direction, with probes re-checked
  afterwards. Blocks lose their cosmetic edge options (`fillet_box` `corner_r`).
- Every block, template and primitive declares probes in its local frame
  (`solid_at`, `empty_at`, `ray` hits, `bbox`, volume-delta sign). `place` transforms
  them to the part frame and adds them to a per-part probe registry.
- The plan contributes step-0 probes: from `interfaces[]` (`position_mm` +
  `diameter_mm`/`size_mm`) and part constraints (single body, envelope). The builder
  never authors probes, so it cannot assert what it built.
- New warm step worker: keeps CadQuery loaded, runs the step list, caches the body after
  each step keyed by the hash of the step prefix, re-runs from the first changed step,
  and after each step checks validity, solid count and the whole probe registry. It
  stops at the first failing step and reports the step, the failing probe(s) and a diff
  against the last good step. Falls back to a cold run if the worker is unavailable.
- Builder-only snapshots: automatic last-good snapshot per step plus named snapshots;
  restore truncates step list and registry; compare reports body diff and which probes
  changed state. Not shown to the user.
- Cheap tier per step (in-process, no STL); mesh checks, thin-wall check and preview
  render only on the final step or on request.
- **BREAKING** Retry semantics: a failing step is not an attempt. An attempt is a plan
  revision. The builder must stop and return `blocked` (reason `probe_stuck`) when the
  same probe fails again after a restore or a different approach; the orchestrator then
  decides plan change, hint, accept or skip.
- The visual auditor stops asking questions that a probe already answered (connected
  body, through-holes, feature presence at a position); it keeps intent and appearance.

## Capabilities

### New Capabilities
- `step-script`: part scripts as an ordered select/resize/place step list over blocks,
  templates and primitives; no raw CadQuery.
- `step-worker`: warm worker that executes the step list with prefix caching, per-step
  cheap checks, stop-at-first-failure reporting, builder-only snapshots, and cold
  fallback.
- `probe-registry`: probe types, local-frame probes declared by every block, template
  and primitive, transform on `place`, plan-derived step-0 probes, and accumulating
  re-check after every step.

### Modified Capabilities
- `subagent-orchestration`: builder loop is no longer "at most 3 attempts"; step
  failures are free, `blocked` is triggered by a repeated probe failure, and an attempt
  is a plan revision.
- `attempt-telemetry`: an `attempts.jsonl` attempt is a plan revision; step failures are
  recorded as step records, not attempts.
- `block-library`: every inventory entry (blocks, templates, primitives) declares probes
  and edge sets; inventory gains primitive entries.
- `planning-phase`: plan instances carry `id`, `params` and `edges`, validated against
  the inventory.
- `print-pose-finishing`: the finishing pass applies plan-declared edge treatments by
  print-pose direction and re-checks probes.
- `parameter-round-trip`: `import-params` is not applicable to step scripts.
- `runtime-boolean-verification`: the "scratch parts require a staged construction plan"
  requirement is replaced; scratch geometry is built from primitive steps whose probes
  and the worker's per-step checks supersede hand-placed `verify_stage` stages.
- `visual-self-review`: the auditor checklist drops questions a passing probe already
  settled.

## Impact

- New: `src/step_worker.py` (worker + client CLI), `src/probes.py` (probe types,
  registry, plan-derived probes), step API in `src/blocks/` (`select`/`resize`/`place`
  helpers), primitive blocks.
- Changed: `build_plan_schema.json` and `plan.py validate` (instance `params`/`edges`);
  `prompts/planning.md` (planner emits instance params); `export_standalone.py` and
  `bundle_project.py` (ship the plan next to the scripts); `write_assembly.py` / the
  finishing pass (edge treatment); every block in `src/blocks/` gains a probe declaration; `inventory.json` and
  its schema; all `templates/*.py` and `templates/archetypes.json`; `script_lint.py`
  (reject raw CadQuery in part scripts); `run_cadquery_model.py` (final-step full tier,
  step records in `--attempts-log`); `log.py` attempt semantics; `render_prompt.py`,
  `prompts/builder.md`, `prompts/part.md`, `prompts/audit.md`; `skill/phase3_build.md`
  (escalation on `probe_stuck`); `reference/scripts.md`, `FILES.md`.
- Unchanged: the `run_cadquery_model.py` JSON contract keys, `build.py`, the quality
  gate, the `CQ_PRINT_ROTATE` mechanism and orientation selection.
- Existing part scripts in user projects keep working through the cold path but are not
  editable by the new builder until converted; evals need their part scripts regenerated.
- No new third-party dependency (worker IPC via stdlib `multiprocessing.connection`).
