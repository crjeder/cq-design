# Phase 3: Build

You are the orchestrator. Builder and auditor agents do all CadQuery authoring and render
review; you own every user checkpoint, the `BUILD_PLAN.json` write-backs, and the
deterministic finish. Do not read reference documents, `inventory.json`, or preview images
into this session for the agents' sake: `src/render_prompt.py` puts what each agent needs
into its prompt file, and the agent reads that file itself.

## Request log

**Appending.** Whenever the user gives a clarification or correction during this phase (a
stage checkpoint, an escalation hint, a design-approval change, a load correction you
announce), before acting on it append one entry to `BUILD_PLAN.json`'s `request_log`:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" request add BUILD_PLAN.json \
    --kind clarification|correction --text "<user's wording, verbatim>" \
    [--level functional|operation|parameter] [--target <part id or part.feature>]...
```
`ts` is stamped automatically. `clarification` answers a question you asked; `correction`
is the user's own initiative. `level`: `functional` adds/removes/reshapes a part or
capability, `operation` changes how a feature is made, `parameter` changes a
dimension/literal only. `add` only appends; it never edits, reorders, or back-fills
existing entries. Skip if the plan has no `request_log`.

**Parameter-level scope.** A `parameter` entry edits the plan values (instance `params`,
`edges`, interface `position_mm`) of its `--target` parts only; a step script holds no
dimensions, so its builder is resumed with no script edit needed. Each such entry starts
the target part's next attempt (attempt = plan revision). Route a value that must agree
across parts through `joints`/`mate_chain.py`, never by hand-editing the sibling's value. Append it with `--snapshot-scripts build/` before
touching any script: the gate diffs the stored hashes and warns `routing_violation` for
a script changed outside the targets that no `joints` entry links to one. The warning
does not block delivery or consume a fix round; surface it to the user.

**Current state only.** When a correction changes the design, in the same turn rewrite
`intent` to the new approved reading and update the affected `part_notes`, deleting
superseded wording (no "ROUND 2", no "previously"). History lives only in `request_log`.
A correction that changes nothing leaves `intent` unchanged. Either way, advance
`intent_ts` in the same turn -- pass `--reconciled` to the `add` above (after rewriting
`intent`); without it `plan.py validate` and the gate fail with `intent not reconciled`.

**Acceptance statements.** When `acceptance.json` exists, every correction also goes to
the oracle: resume the same oracle agent (or render and spawn it as in Phase 1, with the
rewritten `intent` as the reformulation) with the correction, show the user any statement
it added, changed or removed, then pass `--acceptance-reconciled` to the `add` (both flags
when both are reconciled in the same turn). The stamp advances even when no statement
changed. Changed statements need re-binding: resume the planner with them. Without the
stamp, validation fails with `acceptance.json not reconciled`.

**Sketches.** An image attached to a clarification or correction is copied to
`sketches/<slug>-<ts>.<ext>` (`:` in `ts` replaced by `-`) and referenced from the entry's
`images` array. Pass sketch paths to the builder in the resume message that acts on them.

**Searching.** For prior context on a decision, run
`python "$SKILL_DIR/src/log.py" request search BUILD_PLAN.json --query <kw>` (plus
`--kind`, `--level`, `--target`) instead of reading the whole log.

## Vocabulary

Every user-facing message follows `skill/phase2_planning.md`'s vocabulary rules (compass
terms, clock positions for rotations). Before acting on a spatial or unagreed feature
reference from the user, restate it with the plan name and its callout badge number
(e.g. "widening `cable_slot` (2)"); when it could mean more than one feature, ask.

## Routing

- **Model.** The `model` field of Step 1's render output (resolved from
  `models.part_author` in `skill_config.json`; absent: Sonnet-class). Do not read
  `skill_config.json` yourself for this. Value `"inline"`: do not spawn; follow the
  rendered builder prompt yourself, returning the same contract to yourself. Builders
  spawn as `cq-design-builder` (fall back to `cq-design:builder` if the project agent is not offered). Auditors always run as fresh `cq-design-auditor` agent (fall back to `cq-design:auditor` if not offered)s
  (pass the render output's `agent_model` as the Agent tool's `model`).
- **Stages** come from the plan's `review_policy` (default `every_stage`): `every_stage`
  stages every part; `checkpoints` stages parts with an interface or 3+ blocks;
  `minimal` stages nothing and skips the profile stub. A user request for "show me each
  step" / "just build it" maps to `--override staged` / `--override autonomous`.
- **One builder per part, sequentially.** Never run builders in parallel (validate runs append to one
  `build/attempts.jsonl`). A part keeps its builder for the whole phase: every later
  change to it resumes that agent (SendMessage), never a new spawn. The auditor is the
  only review agent.
- Under `minimal`, proceed on reversible decisions without asking and surface the
  builders' `decisions` at the design approval checkpoint.

## Part loop

For each part in `plan["parts"]`, in order (skip any part with `copy_of`: it has no script;
`write_assembly.py` builds it from its source part's geometry, so build the source first):

1. **Render** the builder prompt:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" builder \
       --plan BUILD_PLAN.json --part <part_id> --attempts build/attempts.jsonl [--override staged|autonomous]
   ```
   It writes `build/<part_id>_prompt.txt` and prints `{"out", "chars", "stages"}`.
2. **Spawn** the `cq-design-builder` agent (`model` = `agent_model` per Routing) with exactly this prompt:
   `Read <out> in full and follow it. Working directory: <absolute cwd>.`
3. **Handle each return** (the builder's JSON contract):
   - `stage_ready` -> **stage checkpoint**: tell the user the stage and `summary`, list
     `preview_paths` so they can open them, and ask. For `profile_stub`: approve /
     change / skip (skip = approve). For other stages: approve / change / finish the rest
     without checkpoints. Resume the builder with `approve`, `change: <verbatim feedback>`,
     or `finish`. After the stub is approved:
     ```bash
     uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
         phase3/stub_approved:<part_id> "<summary>"
     ```
   - `passed` -> **Implementation audit** below.
   - Any contract whose `step_report` has `unmanaged_edit: true` (the builder changed its
     script outside `script_ops.py`): list it with that part's `decisions` at the design
     approval checkpoint. It does not block the audit.
   - `blocked` -> **Escalation** below.

Preview images stay out of this session unless the user asks you to look at one.

## Dimension edits

A changed measurement is one `Edit` of its constant in `parameters.py`. Then run
`plan.py validate BUILD_PLAN.json`: it prints `Resolved params changed for: <parts>`.
Rebuild, re-gate and re-audit only those parts; leave the others untouched. Do not
hand-edit plan params that are expressions.

## Escalation

On `blocked` (`blocked_reason` `probe_stuck`: the same probe failed again after a
different approach or a restore; `missing_block`: the geometry needs a block or primitive
the inventory lacks):
1. Summarize `error_summary` -- the stuck probe (plan-owned probes trace to a plan
   interface or the envelope) or the missing geometry -- and ask: change the plan, give a
   hint, accept as-is, or skip the part.
2. **Plan change** -> log the user's wording with `log.py request add ... --target
   <part_id>` (this starts the part's next attempt), edit the plan entry the probe came
   from (or add the missing instance), re-validate the plan, then resume the same builder
   with `fix: plan changed: <what changed>`.
3. **Hint** -> resume the same builder with `fix: <hint verbatim>`.
4. **Accept as-is** -> accept the last render; skip the audit; do the write-backs.
5. **Skip** -> move on without this part; say so at design approval.

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
    phase3/escalation:<part_id> "<hint verbatim | accepted as-is | skipped>"
```

On **accept as-is**, also append (resume keys on it):
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
    phase3/part_accepted:<part_id> "accepted as-is at escalation"
```

## Implementation audit

1. Render and spawn a fresh `cq-design-auditor` agent for every `passed` contract:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" audit \
       --plan BUILD_PLAN.json --part <part_id> --script build/<part_id>.py \
       --previews <preview_paths from the contract...> \
       --step-report build/<part_id>.step_report.json
   ```
   With a passing step report the audit drops the connectedness question and the
   presence/position questions of probed interfaces (the probes settled them);
   `unprobed_interfaces` are still asked. Omit `--step-report` for a legacy script.
   Prompt: `Read build/<part_id>_audit_prompt.txt in full and follow it. Working directory: <absolute cwd>.`
2. **`verdict: pass`** -> accepted. Do the write-backs, then:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
       phase3/part_accepted:<part_id> "audit passed"
   ```
   and report any `findings` to the user under their own "Advisory" heading.
3. **`verdict: fail`** -> write the auditor's JSON contract to `build/<part_id>_audit.json`,
   then record the verdict on the builder's last attempt:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" attempt audit-fail \
       --part <part_id> --audit build/<part_id>_audit.json
   ```
   Resume the builder with `fix:` listing each failed question, its view, discrepancy, and
   any `missing_views`, then re-audit its new contract with a fresh auditor. One such
   round; a second fail goes to **Escalation**. A failed question that names an acceptance
   statement (`S<n>`, a user-approved `visual` statement) gets up to 3 rounds; still
   failing after the third, escalate it with the `oracle_unmet` choices (Quality gate).
   The progressive self-review answers the same `S<n>` questions, listed in the audit
   prompt.

## Write-backs on acceptance

Mark the accepted script (also on **accept as-is**); the gate loop restores to it:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/script_history.py" mark accepted build/<part_id>.py
```

From the accepted contract, into that part's `BUILD_PLAN.json` entry:
- `placement` (replacing any planner proposal). Write nothing when it is `null`; a
  mate-chained part never carries `placement`. Tell the user only when it replaces a
  differing value.
- `engineering_rationale`, exactly as returned.

If a legacy part script's `PARAMETERS` block was hand-edited, reconcile with
`uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan.py" import-params build/<part_id>.py --part <part_id> --write`
instead of hand-editing the plan (a step script reports `not_applicable`: its values are
already the plan's).

## Design approval checkpoint

When every part is accepted (or skipped), list every part's final preview paths in one
message, plus the builders' `decisions` and any unresolved advisories, and ask:

> Here's every part as modeled. Does this match what you had in mind? Reply to approve,
> or describe what to change.

- **Approve** -> print orientation.
- **Change** -> log it, resume each affected part's builder with `fix: <feedback>`,
  re-audit, re-present this checkpoint.

Skip the wait only when the user asked for a fully autonomous run (still list the
previews). Then:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
    phase3/design_approved "<n> parts"
```

## FEM stress advisor

Only for a part whose plan `load` declares `magnitude_n`, `applied_at`, and
`grounded_at` (see `prompts/planning.md` rule 10) -- most parts
skip this section entirely. It is an **advisor**, never a gate: it never blocks
acceptance and adds no quality-gate stage. Run it once the part's script is accepted
(the geometry it solves on should be final):

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py --deliver --formats step --output-dir build
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/fem_check.py" \
    build/<part_id>.step --plan BUILD_PLAN.json --part <part_id> \
    --mesh-size <mm> > build/<part_id>.fem_stress.json
```

The advisor solves only the part's wall-thickness shell, not its full solid volume (see
`reference/scripts.md`, `src/fem_check.py`) -- the shell (`constraints.wall_min_mm`, echoed in the result's
`mesh.shell_thickness_mm`) is now the thinnest feature in the model by construction. Pick
`--mesh-size` as a fraction of *that* thickness (a starting point, not a rule -- there is
no derived default); a mesh size comparable to or larger than
the shell thickness risks too few elements through the wall to resolve at all (a singular
or near-singular solve). Read the result:

- **`status: "skipped"`** -- report the reason and move on; nothing else in the loop
  changes. This is the common case for most load-bearing parts (no researched mass, or
  the `fem` dependency group is not installed).
- **`status: "ok"`** -- write the failure index and location into
  `engineering_rationale.check`/`worst_case_stress` (see `prompts/part.md`'s Engineering
  rationale section) instead of a closed-form derivation. If `hint` says a stress
  concentration (peak near a sharp corner), consider a fillet/chamfer edit and re-run
  the part loop; if it says a distributed/undersized section, consider thickening.
  Neither is required -- the number is advisory, the author decides.
- **Implausible result** (extreme `concentration_ratio`, a peak location the geometry
  doesn't explain, an `fi_p99` that doesn't match the loading) -- re-run at half the
  `--mesh-size` and compare `fi_p99` between the two runs before citing either; a value
  that moves substantially means the coarser mesh wasn't converged.

`build/<part_id>.fem_stress.json` (when `"ok"`) feeds `print_orientation.py --fem-stress`
below.

## Toolpath-speed advisor

Runs for every part (no plan input required, unlike the FEM advisor above); it is an
**advisor**, never a gate. It re-runs the part script and reports how much sharp
corners and small features cost in print time -- a build-pose hint, since no print
orientation exists yet:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/toolpath_speed.py" \
    --plan BUILD_PLAN.json --script build/<part_id>.py
```

Read the result:

- **`status: "skipped"`** -- `profile.json` has no `motion` block, or the
  geometry isn't prismatic enough for the model; report the reason and move on.
- **`status: "ok"`, `issues: []`** -- already efficient; nothing to report.
- **An issue with `attribution`** -- ranked corners and the print time each fillet
  would recover. Consider raising the radius at the top few, largest first; this is
  conditional on the part's eventual build orientation (a corner vertical here may
  print horizontal), so re-check after orientation is chosen if the finding is close
  to the reporting threshold.
- **An issue with `dominant: "crowding"`** -- the part's features are too small to
  ever reach cruise speed; no single edge is at fault. Consider fewer, larger features
  rather than filleting individual edges.

Neither is required -- the number is advisory, the author decides. This finding is
revisited with real numbers (the accepted orientation, and the layer-time/stall model)
at the quality gate and reported in `skill/phase4_deliver.md` step 1.

## Print-orientation optimization

Per union, on its build-pose STL (all directions here are build pose; orientation is a property of the part, not its
assembled pose), using the part's effective `optimize_for` (default `strength`). A part
without declared `unions` has one union whose id is its part id:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py --deliver --formats stl --output-dir stl
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/print_orientation.py" \
    stl/<union_id>.stl --overhang-max-deg <overhang_max_deg> \
    --optimize-for <strength|min_support|visual_quality|min_build_height|min_print_time> \
    --source-script build/<part_id>.py \
    [--load x,y,z] [--load-type tension|compression|bending|shear] [--show-face x,y,z] \
    [--fem-stress build/<part_id>.fem_stress.json] \
    [--speed-model build/<union_id>.speed_candidates.json]
```

Pass `--load`/`--load-type` from the plan's `load`, `--show-face` when declared, and
`--fem-stress` when the FEM advisor above produced an `"ok"` result for this part -- it
replaces the load-direction cosine with the solved failure index per candidate.
`--speed-model` (needed only for `min_print_time`, or to have the estimated print time
reported in the rationale under any mode) takes a `toolpath_speed.py --emit-candidates`
result:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/toolpath_speed.py" \
    --plan BUILD_PLAN.json --script build/<part_id>.py --stl stl/<union_id>.stl \
    --emit-candidates <union_id> > build/<union_id>.speed_candidates.json
```

- **Sanity-check the load first.** A compression part (base, foot, plinth) or a
  non-load-bearing cover scored as tension gets tipped onto an edge; check
  `build_height_mm` and the rotation against common sense. If the plan's `load` is wrong
  or missing for a real load, correct `load` in `BUILD_PLAN.json`, tell the user, and
  re-run.
- **Accept** when the mode's primary score is acceptable or no comparable pose is better.
- **Improve** a genuinely poor primary score by resuming the part's builder with
  `fix: <geometry edit, e.g. chamfer the overhang at ...>`, re-auditing, and re-running.
- `min_support` / `visual_quality` may accept a weaker pose on purpose; surface a trade-off
  that looks unacceptable instead of overriding the mode.

Write the accepted results to `build/orientations.json` (`{"<union_id>": {...result}}`)
and one `build/<union_id>.orientation.json` per union, then:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
    phase3/orientation_chosen "<n> unions, see build/orientations.json"
```

## Print finishing

Orientation-dependent features (teardrop peak direction) are authored through
`blocks.print_up()`, which returns +Z until the accepted pose is known. No separate
command: `write_assembly.py --orientations build/orientations.json` (next section),
and later `build/build.py`, re-load each part script with `CQ_PRINT_ROTATE` set to that part's accepted `rotate`,
so the assembly and the deliverables carry the finished geometry with no builder round. Only a part
script that mentions `print_up` changes; others are unaffected. To check a single script
under a pose, add `--print-rotate build/<union_id>.orientation.json` to `run_cadquery_model.py`.

The assembly step re-scores orientation on each finished `print_up` part and returns advisory
`pose_findings` (`pose_shift`) if the optimizer would now choose a different pose; the
accepted pose is kept. Surface them in the delivery report. The manifest records
the `print_rotate` used per union (`freshness.pose_stale_ids` flags a mismatch after
orientation is re-accepted). A `copy_of` part and a multi-union part whose orientation is
keyed by union id are loaded pose-free (+Z).

## Write assembly

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan.py" validate BUILD_PLAN.json --require-rationale
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/write_assembly.py" \
    --plan BUILD_PLAN.json --parts-dir build --out stl \
    --orientations build/orientations.json
```

A validation failure blocks the step. It writes `stl/<union_id>.stl` per union in
**assembled** pose and one `stl/keep_out__*.stl` per declared zone for the whole-model
checks, plus `stl/export_manifest.json`. It writes no user-facing file: `model.3mf`, plate
STLs and the other formats come from `build/build.py` in Phase 4.

Then make the working directory a self-contained uv project that builds the model files
without the skill:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/bundle_project.py" .
uv sync
```

`write_assembly.py` journals `phase3/assembly_written` itself; do not append it.

## Quality gate

Once per union:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/quality_gate.py" \
    --script build/<part_id>.py --plan BUILD_PLAN.json \
    --stl-dir stl --orientation build/<union_id>.orientation.json \
    > build/<union_id>.quality_gate.json
```

The gate prints its report to stdout only; the redirect is what writes the file. Exit 1
means `passed: false`, not a crash: the report is still written. Read
`build/<union_id>.quality_gate.json`. The gate is report-only (never pass `--fix`). Route each
finding by its own `action` field, not by its `type`:

- **`fix`** -> resume the part's builder with `fix: <type>: <message> (hint: <hint>)`,
  re-audit if geometry changed, re-export, re-run the gate with
  `--previous build/<union_id>.quality_gate.json` (copy the previous report aside first,
  e.g. to `build/<union_id>.quality_gate.round<n>.json`, and pass that copy). Read its `delta`:
  - `resolved` empty or `regressed` non-empty -> the round made nothing better: undo it
    before anything else, never by editing the script back:
    ```bash
    uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/script_history.py" restore accepted build/<part_id>.py
    ```
    and start the next round's resume with `fix: previous edit reverted (<delta>): ...`.
  - otherwise keep the edit and re-run `script_history.py mark accepted build/<part_id>.py`.

  At most 2 rounds per part; then summarize the remaining findings to the user. If the
  last round was reverted, first re-export and re-run the gate from the restored script,
  so the delivered files come from `accepted`.
- **`oracle_unmet`** (`source: "oracle"`) is an acceptance statement the built part does
  not meet. It routes as `fix` like the rest, but its rounds are counted by the gate, not
  by the 2-round cap above: each issue carries `round` (from `--previous`), and the gate
  sets its action to `ask_user` at round 3. Quote the statement in the `fix:` resume.
  At `ask_user`, offer: amend the intent (a correction; re-runs the oracle), accept as-is,
  or skip the part.
- **`re_export`** -> the STL predates an edit: re-run the model export, then the gate. No
  builder involved.
- **`ask_user`** -> surface the finding's `message` and `hint` and ask before doing
  anything; the gate can't pick the remedy on its own (e.g. relieve geometry vs. fix the
  plan's `kinematics` entry; narrow `required_range` vs. relieve a limited stop). Describe
  ranges as clock positions per the vocabulary rules.
- **`warn_only`** -> never triggers a fix round; show it with the print recipe.

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
    phase3/gate_result "<pass|escalated>, <n> remaining findings"
```
Then proceed to Phase 4.

## Post-delivery corrections

A user request that changes geometry (a dimension, a feature, a hand-edit to a part
script) arriving after Phase 4 has already reported delivery is still a correction --
log it (Request log, above), resume the affected part's builder, re-audit -- but it also
re-opens every deterministic step downstream of that union that Phase 4 already reported
as done: **re-run Print-orientation optimization for the affected union(s)** (unaffected
unions keep their accepted `build/orientations.json` entry), **then Write assembly and
`build/build.py`, then Quality gate**, before repeating Phase 4's delivery report.
