# Phase 3: Build

You are the orchestrator. Builder and auditor agents do all CadQuery authoring and render
review; you own every user checkpoint, the `BUILD_PLAN.json` write-backs, and the
deterministic finish. Do not read reference documents, `inventory.json`, or preview images
into this session for the agents' sake: `src/render_prompt.py` puts what each agent needs
into its prompt file, and the agent reads that file itself.

## Request log

**Appending.** Whenever the user gives a clarification or correction during this phase (a
stage checkpoint, an escalation hint, a design-approval change, a load correction you
announce), append one entry to `BUILD_PLAN.json`'s `request_log` before acting on it:
`{"ts": "<UTC ISO-8601>", "kind": "clarification" | "correction", "text": "<user's wording,
verbatim>", "level": "functional" | "operation" | "parameter", "targets": ["<part id or
part.feature>", ...]}`. `clarification` answers a question you asked; `correction` is the
user's own initiative. `level`: `functional` adds/removes/reshapes a part or capability,
`operation` changes how a feature is made, `parameter` changes a dimension/literal only.
Append only; never edit, reorder, or back-fill existing entries. Skip if the plan has no
`request_log`.

**Current state only.** When a correction changes the design, in the same turn rewrite
`intent` to the new approved reading and update the affected `part_notes`, deleting
superseded wording (no "ROUND 2", no "previously"). History lives only in `request_log`.
A correction that changes nothing leaves `intent` unchanged.

**Parameter scope.** A `parameter`-level entry changes literals only in the parts it
targets. A value that must agree across parts routes through `joints` / `mate_chain.py`,
never by copying the literal into a sibling part.

**Sketches.** An image attached to a clarification or correction is copied to
`sketches/<slug>-<ts>.<ext>` (`:` in `ts` replaced by `-`) and referenced from the entry's
`images` array. Pass sketch paths to the builder in the resume message that acts on them.

**Searching.** For prior context on a decision, run
`python "$SKILL_DIR/src/request_log_search.py" BUILD_PLAN.json --query <kw>` (plus
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
  rendered builder prompt yourself, returning the same contract to yourself. Auditors
  always run as fresh agents on the session default.
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

For each part in `plan["parts"]`, in order:

1. **Render** the builder prompt:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" builder \
       --plan BUILD_PLAN.json --part <part_id> --attempts build/attempts.jsonl [--override staged|autonomous]
   ```
   It writes `build/<part_id>_prompt.txt` and prints `{"out", "chars", "stages"}`.
2. **Spawn** the builder (model per Routing) with exactly this prompt:
   `Read <out> in full and follow it. Working directory: <absolute cwd>.`
3. **Handle each return** (the builder's JSON contract):
   - `stage_ready` -> **stage checkpoint**: tell the user the stage and `summary`, list
     `preview_paths` so they can open them, and ask. For `profile_stub`: approve /
     change / skip (skip = approve). For other stages: approve / change / finish the rest
     without checkpoints. Resume the builder with `approve`, `change: <verbatim feedback>`,
     or `finish`. After the stub is approved append
     `- phase3/stub_approved:<part_id>: <summary>` to `build/journal.md`.
   - `passed` -> **Implementation audit** below.
   - `blocked` -> **Escalation** below.

Preview images stay out of this session unless the user asks you to look at one.

## Escalation

On `blocked`:
1. Summarize `error_summary` and ask: give a hint, accept as-is, or skip the part.
2. **Hint** -> resume the same builder with `fix: <hint verbatim>`.
3. **Accept as-is** -> accept the last render; skip the audit; do the write-backs.
4. **Skip** -> move on without this part; say so at design approval.

Append `- phase3/escalation:<part_id>: <hint verbatim | accepted as-is | skipped>` to
`build/journal.md`.

## Implementation audit

1. Render and spawn a fresh auditor for every `passed` contract:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" audit \
       --plan BUILD_PLAN.json --part <part_id> --script build/<part_id>.py \
       --previews <preview_paths from the contract...>
   ```
   Prompt: `Read build/<part_id>_audit_prompt.txt in full and follow it.`
2. **`verdict: pass`** -> accepted. Do the write-backs, append
   `- phase3/part_accepted:<part_id>: audit passed` to `build/journal.md`, and report any
   `findings` to the user under their own "Advisory" heading.
3. **`verdict: fail`** -> record the verdict on the builder's last attempt:
   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/telemetry.py" append build/attempts.jsonl \
       --field 'part_id=<part_id>' --field 'attempt=<contract attempts>' --field 'outcome=fail' \
       --field 'error_types=["visual_mismatch"]' --field 'prompt_chars=<chars>' --field 'model=<builder model>' \
       --field 'visual_review={"passed": false, "failed_question": "<first failed question>"}'
   ```
   Resume the builder with `fix:` listing each failed question, its view, discrepancy, and
   any `missing_views`, then re-audit its new contract with a fresh auditor. One such
   round; a second fail goes to **Escalation**.

## Write-backs on acceptance

From the accepted contract, into that part's `BUILD_PLAN.json` entry:
- `placement` (replacing any planner proposal). Write nothing when it is `null`; a
  mate-chained part never carries `placement`. Tell the user only when it replaces a
  differing value.
- `engineering_rationale`, exactly as returned.

If a part script's `PARAMETERS` block was hand-edited, reconcile with
`uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/import_params.py" build/<part_id>.py --part <part_id> --write`
instead of hand-editing the plan.

## Design approval checkpoint

When every part is accepted (or skipped), list every part's final preview paths in one
message, plus the builders' `decisions` and any unresolved advisories, and ask:

> Here's every part as modeled. Does this match what you had in mind? Reply to approve,
> or describe what to change.

- **Approve** -> print orientation.
- **Change** -> log it, resume each affected part's builder with `fix: <feedback>`,
  re-audit, re-present this checkpoint.

Skip the wait only when the user asked for a fully autonomous run (still list the
previews). Then append `- phase3/design_approved: <n> parts` to `build/journal.md`.

## Print-orientation optimization

Per union, on its part-frame STL (orientation is a property of the part, not its
assembled pose), using the part's effective `optimize_for` (default `strength`):

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py --deliver --formats stl --output-dir stl
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/print_orientation.py" \
    stl/<part_id>.stl --overhang-max-deg <overhang_max_deg> \
    --optimize-for <strength|min_support|visual_quality> \
    --source-script build/<part_id>.py \
    [--load x,y,z] [--load-type tension|compression|bending|shear] [--show-face x,y,z]
```

Pass `--load`/`--load-type` from the plan's `load`, `--show-face` when declared.

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

Write the accepted results to `build/orientations.json` (`{"<part_id>": {...result}}`)
and one `build/<part_id>.orientation.json` per union, then append
`- phase3/orientation_chosen: <n> unions, see build/orientations.json` to
`build/journal.md`.

## Model export

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json --require-rationale
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/model_export.py" \
    --plan BUILD_PLAN.json --parts-dir build --out . --stl-out stl \
    --orientations build/orientations.json
```

A validation failure blocks the export. The export writes `model.3mf` (each union a named
object in print pose, with plate metadata), fused `stl/plate_<n>.stl` per multi-union plate
(print pose), and `stl/<part_id>.stl` per union in **assembled** pose for the whole-model
checks.

Then make the working directory a self-contained uv project that regenerates the plates
without the skill:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/bundle_project.py" .
uv sync
uv run python build/build.py
```

Append `- phase3/model_exported: model.3mf + <n> STL(s) written` to `build/journal.md`.

## Quality gate

Once per union:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/quality_gate.py" \
    --script build/<part_id>.py --plan BUILD_PLAN.json \
    --stl-dir stl --orientation build/<part_id>.orientation.json
```

Read `build/quality_gate.json`. The gate is report-only (never pass `--fix`).

- **`severity: error`** -> resume the part's builder with `fix: <type>: <message> (hint:
  <hint>)`, re-audit if geometry changed, re-export, re-run the gate. At most 2 rounds per
  part; then summarize the remaining errors to the user.
- **`stale_artifact`** -> the STL predates an edit: re-run the model export, then the gate.
- **`motion_collision`** -> names the binding value and `colliding_union`: relieve that
  geometry, or fix the plan's `kinematics` entry if the declared range is wrong.
- **`plate_clearance`** -> co-plated unions within one layer height fuse: widen the gap.
- **`range_exceeds_limit`** -> the required range exceeds the joint's mechanical limit:
  change the range or the joint.
- **Warnings** (`contact_limited_stop`, `range_check_not_applicable`, `edge_treatment`,
  `cosmetic_slope`, `check_skipped`) never trigger a fix round; show them with the print
  recipe. For `contact_limited_stop`, ask whether the natural stop is the intended rest
  position (then narrow `required_range`) or should be relieved. Describe ranges as clock
  positions per the vocabulary rules.

Append `- phase3/gate_result: <pass|escalated>, <n> remaining findings` to
`build/journal.md`, then proceed to Phase 4.

## Post-delivery corrections

A user request that changes geometry (a dimension, a feature, a hand-edit to a part
script) arriving after Phase 4 has already reported delivery is still a correction --
log it (Request log, above), resume the affected part's builder, re-audit -- but it also
re-opens every deterministic step downstream of that union that Phase 4 already reported
as done: **re-run Print-orientation optimization for the affected union(s)** (unaffected
unions keep their accepted `build/orientations.json` entry), **then Model export, then
Quality gate**, before repeating Phase 4's delivery report.
