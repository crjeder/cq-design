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

- **Model.** `models.part_author` in `skill_config.json` (absent: Sonnet-class). Value
  `"inline"`: do not spawn; follow the rendered builder prompt yourself, returning the
  same contract to yourself. Auditors always run as fresh agents on the session default.
- **Stages** come from the plan's `review_policy` (default `every_stage`): `every_stage`
  stages every part; `checkpoints` stages parts with an interface or 3+ blocks;
  `minimal` stages nothing and skips the profile stub. A user request for "show me each
  step" / "just build it" maps to `--override staged` / `--override autonomous`.
- **One builder per part, sequentially.** Never run builders in parallel (the telemetry
  hook appends to one file). A part keeps its builder for the whole phase: every later
  change to it resumes that agent (SendMessage), never a new spawn. The auditor is the
  only review agent.
- Under `minimal`, proceed on reversible decisions without asking and surface the
  builders' `decisions` at the design approval checkpoint.

## Part loop

For each part in `plan["parts"]`, in order:

**Step 0 — Profile stub review**

Before rendering the full part prompt (Step 1 below), author a minimal stub script:
the part's characteristic 2D profile (from `dimensions` and, when it drives the
outline, `part_notes`/`interfaces`), extruded to a nominal thickness. Write it to a
throwaway path (e.g. `build/<part_id>_stub.py`, not `build/<part_id>.py`) and render it:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>_stub.py --preview --preview-dir preview
```

This reuses the existing preview path; no new renderer is introduced. The stub is
disposable — it is never reused as progressive build's base-shape stage, and its
geometry is not required to match the construction plan later used for that stage
(see the Progressive build section below).

Branch on the plan's effective `review_policy` (see Build mode above):

- **`checkpoints` or `every_stage`:** display the rendered stub and a one-line
  description of the profile, then wait. The user can **approve** (proceed to Step 1),
  **request a change** (re-author the stub with the feedback, re-render, present the
  checkpoint again), or **skip** (proceed to Step 1 without further stub iteration).
- **`minimal`:** still render the stub, but evaluate it yourself against the part's
  design intent (does the silhouette look right) without pausing for the user —
  the same self-review posture already used for autonomous parts' geometry. Note any
  mismatch as a one-line self-correction and adjust the upcoming full script
  accordingly; do not block on it.

Once the stub is approved (or self-reviewed under `minimal`), append one line to
`build/journal.md` (see `skill/resume.md`):

```
- phase3/stub_approved:<part_id>: <one-line profile description>
```

Then attempt up to **3 times**:

**Step 1 — Render the part prompt**

Read `$SKILL_DIR/prompts/part.md` and substitute every placeholder. The rendering
**mode** is set by where this prompt ends up being read, and the `{{CQ_REFERENCE}}` /
`{{FDM_GUIDELINES}}` rows below are mode-keyed:

- **Inline** — the prompt is authored and consumed in the **main session's own
  context**, which already holds the Phase 3 setup reads. Today this is only a
  **progressive part's** per-stage authoring (see Progressive build). Substitute
  with a citation, not file contents.
- **Cold** — the prompt is sent to a context with no ambient reads of its own: a
  spawned **builder agent** (every autonomous part, per the Agent routing gate —
  an Agent-tool spawn starts fresh with none of main's context, even though main
  renders Step 1 before spawning it) or a future `claude -p` subprocess (item 15's
  routed part authoring). Substitute with full file contents.

A retry within the part loop (Step 2's "On retry attempts") re-renders Step 1 in the
same mode as the attempt it is retrying — a builder agent's retries stay cold, a
progressive part's retries stay inline; a part never switches modes mid-build.

| Placeholder | Value |
|-------------|-------|
| `{{PART_ID}}` | `part["id"]` |
| `{{PART_DESCRIPTION}}` | `part["description"]` |
| `{{W_MM}}` | `part["dimensions"]["w_mm"]` |
| `{{D_MM}}` | `part["dimensions"]["d_mm"]` |
| `{{H_MM}}` | `part["dimensions"]["h_mm"]` |
| `{{INTERFACES}}` | `part["interfaces"]` as JSON, or `(none)` |
| `{{POSE_INTENT}}` | `part["pose_intent"]`, or `(none)` -- present in both cold and inline render modes |
| `{{PART_NOTES}}` | `part["part_notes"]`, or `(none)` -- for a part with no matching blocks, this is the ONLY place the design intent for its scratch geometry is recorded (see `prompts/planning.md` rule 3); never omit this substitution when the field is present |
| `{{BLOCK_SPECS}}` | For each block in `part["blocks_needed"]`: look up in inventory, format as `- **name** — use\n  params: k (v), ...`; `(none — use raw CadQuery primitives)` if list is empty |
| `{{WALL_MIN_MM}}` | `plan["constraints"]["wall_min_mm"]` |
| `{{OVERHANG_MAX_DEG}}` | `plan["constraints"]["overhang_max_deg"]` |
| `{{MATERIAL}}` | `plan["material"]` |
| `{{NOZZLE_MM}}` | `plan["nozzle_mm"]` |
| `{{CQ_REFERENCE}}` | **Cold** (builder agent / future `claude -p`): full contents of `CadQuery Pattern Reference.md`, then the full contents of `CadQuery Anti-Patterns.md` (appended **always**, for every part), then `emboss_text.md` **only when this part involves text/emboss** (its `description`, `part_notes`, or any `interfaces` entry mentions text/engrave/emboss/label; otherwise omit it — the pattern reference already carries the basic `.text()` idiom). **Inline** (progressive part, main session): a citation naming `reference/CadQuery Pattern Reference.md` and `reference/CadQuery Anti-Patterns.md` as already-in-context documents to apply, do not paste their contents; name `reference/emboss_text.md` too under the same text/emboss gate. |
| `{{FDM_GUIDELINES}}` | Sections from `FDM 3D Print Design Guidelines.md` whose `applies_to` tag includes any block in `blocks_needed`, plus all sections tagged `always`. **Cold:** inject those sections' full text. **Inline:** cite the same selected sections by name only (the tag-filter computation is unchanged; only whether its output is bodies or names differs by mode). |
| `{{ENGINEERING_RULES}}` | Sections from `Engineering Design Rules.md` whose `applies_to` tag includes any block in `blocks_needed`, plus all sections tagged `always`, plus all load-relevant sections when `part["load"]` is declared (any type), plus the "Flush-Fold Hinge Standoff" section when any entry in the plan's top-level `kinematics` array names this part as `moving_union` (block-based or block-free, per `blockless-kinematics`). **Cold:** inject those sections' full text. **Inline:** cite the same selected sections by name only. |

**Measuring the render.** Write the fully-substituted prompt text (the same text
handed to the builder agent in cold mode, or the same text this session is now acting on
in inline mode) to `build/<part_id>_prompt_attempt<n>.txt` before proceeding. This is
the source for Step 5's `prompt_chars` field — never type or estimate that number, only
report a count computed from this file (e.g. `python -c
"import pathlib;print(len(pathlib.Path('build/<part_id>_prompt_attempt<n>.txt').read_text(encoding='utf-8')))"`).
A typed guess is not telemetry; a self-reported prompt_chars value from before this
instrumentation existed is not comparable to one measured this way (see `attempt-telemetry`
design D7).

**Step 1.5 — Match archetype**

Before authoring from a blank file, check whether `templates/archetypes.json` has a
known-good template for this part's shape:

1. **Planned value.** If `part["archetype"]` is set (the planner's rule 3a match), look up
   that entry's `use` description and confirm it actually fits this part's `description` /
   `part_notes` / `interfaces`. A confirmed fit skips straight to step 3 below.
2. **No planned value, or the planned value doesn't fit.** Scan `templates/archetypes.json`
   for an entry whose `use` or `aliases` matches this part's shape. No entry read here needs
   its full script contents yet -- match on `name`/`use`/`aliases` only.
3. **Match found (planned or newly matched).** Author the part script by copying
   `templates/<file>` verbatim into `build/<part_id>.py`, then edit its top-level
   `PARAMETERS` block to this part's dimensions/positions and apply any needed deltas
   (added/removed features) -- preserving the template's existing `cq_verify` guards
   rather than stripping them. This replaces Step 2's from-scratch authoring for this part;
   Steps 2.5 onward (lint, validate, review) run unchanged against the resulting script.

   **Add the ENGINEERING RATIONALE block.** A copied template has no rationale
   section of its own (it was written once, generically, for no specific part's
   parameters) -- the archetype path does not render `prompts/part.md`, so nothing
   else inserts one. Apply the same trigger as `prompts/part.md`'s Engineering
   rationale section (declared plan `load`, or `blocks_needed`/`archetype` in the
   load-bearing set) to decide full vs. one-line form, then insert the section
   between PARAMETERS and the geometry, evaluating the check against the
   just-edited PARAMETERS values -- not the template's original defaults.
4. **No match.** Fall back to raw authoring (Step 2 below) and state in one line why no
   archetype fit (e.g. "no archetype fits: this is a multi-cavity organizer tray, not a
   single enclosure/lid/bracket shape").

A retry within the part loop does not re-run this match -- it edits the already-authored
script (from either path) per Step 2's "On retry attempts".

**Step 2 — Write the part script**

Write `build/<part_id>.py`. The script must open with a flat import line for every block in `blocks_needed` — the `blocks` package re-exports every block, so no submodule path is needed:

```python
from blocks import fillet_box, screw_boss    # example
```

Then a `PARAMETERS` block, then the geometry, then `result = ...`. See generated-script rules in the core SKILL.md.

**Multi-union parts.** When the part declares a `unions` array in `BUILD_PLAN.json` (one script
that builds several rigid bodies in one coordinate frame, e.g. both leaves of a print-in-place
hinge), set `result` to a **dict** mapping each declared union id to its `Workplane` --
`result = {"leaf_a": <wp>, "leaf_b": <wp>}` -- with keys exactly the declared union ids. Each
union is then exported, posed, and kinematically/clearance checked as a distinct body. A part
without a `unions` array keeps the single `result = <wp>` form (one union, id = part id).

On retry attempts: review the error types and hints from the previous attempt, apply targeted fixes. Do not start over blindly — you have full planning context. Keep the fix inside what the reported error implicates: do not restructure, refactor, or rewrite parts of the script the error does not name, and do not take the retry as an opening to add features or guards the spec did not ask for.

**Rationale survives retries.** A correction prompt never waives the ENGINEERING
RATIONALE requirement (see `prompts/part.md`). If the fix changes a parameter that
appears in the rationale's computed check, re-evaluate that check with the new value
in the corrected script — don't leave a stale number that no longer matches the
parameters it claims to check.

**Step 2.5 — Lint before validate**

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/script_lint.py" build/<part_id>.py
```

Pure-stdlib AST lint, no CadQuery subprocess — catches mechanically-detectable
anti-patterns (a boolean inside a loop, a missing `result`, a submodule block
import, a direct `cq.exporters.export` call, a magic number outside the named
parameters, an unre-anchored `.center()`/`.hole()` chain, an unguarded
computed-offset boolean, `.shell()` after `.fillet()`, `.fillet()` after
`.chamfer()` in the same chain) in milliseconds instead of a full run. Exit 0 means no findings — proceed to Step 3. Exit 1 prints
`{"success": false, "findings": [...]}`; fix every finding in the script and
re-lint before spending the first `run_cadquery_model.py` call.

**Step 3 — Validate**

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py \
    --expected-dims <w_mm>,<d_mm>,<h_mm> \
    --dim-tolerance <dimension_tolerance_mm> \
    --wall-min <wall_min_mm> \
    --preview --preview-dir preview \
    --cross-sections \
    --callout "name=<name>;center=<x>,<y>,<z>" [...one per named+positioned interface] \
    --unlocated-name <name> [...one per named interface with no position_mm]
```

`--preview-dir preview` writes the preview PNG(s) to the project's `preview/` directory
instead of alongside the script, keeping `build/` free of generated images.

**Thread the part's agreed vocabulary onto the tile.** For each of this part's
`interfaces[]` entries that declares both `name` and `position_mm`, add one
`--callout "name=<name>;center=<x>,<y>,<z>"` (plan order -- badge numbers follow
supply order); for each named interface with no `position_mm`, add one
`--unlocated-name <name>`. This makes the tile the checkpoint's vocabulary-
ratification artifact (design D2/D3 of `shared-feature-vocabulary`): every agreed
feature name gets a numbered badge and a legend line, or an explicit "not located"
listing, so later conversation can reference features by name and badge instead of
re-describing their location in prose.

Parse the JSON result. Blocking error types: `non_manifold_edge`, `non_watertight`, `disconnected_body`, `dimension_mismatch`, `occ_exception`, `construction_error`, `command_not_done`, `fillet_failure`, `null_object`, `index_out_of_range`, `type_mismatch`.

The `--preview` overview is a **2x2 first-angle tile** (Front, Left side, Top,
Isometric); `--cross-sections` writes the interior sections as **separate files**
(`previews[1:]`), not into the tile. Pass the declared feature/union positions from
`BUILD_PLAN.json` as `--extra-section` cuts so the review's connectedness and
interior questions have a section that actually crosses the geometry.

**Sections through declared positions.** With no positions, `--cross-sections` cuts
X/Y/Z through the bounding-box center only. If this part unions a feature (a boss,
tab, dovetail, rib) into a body that already has a cavity (pit, pocket, shell)
elsewhere in the same script, or joins bodies at a junction away from the center, the
center cuts will not pass through it — and a disconnection or a feature poking into a
cavity is invisible from every exterior panel (see `CadQuery Pattern Reference.md`
gotcha 12). Add one `--extra-section axis=value_mm` per such position (repeatable),
e.g. `--extra-section x=50 --extra-section x=110` for two seam tabs at x=50 and x=110,
so the Step 4 review has a section crossing each feature/junction to answer against.
When `--extra-section` positions are given they replace the center cuts (they are the
declared positions); each is written as its own `<part>_section_<axis>_<pos>mm.png`.

**Feature detail previews for small features.** The default overview tile packs the
four views into a compact 2x2 grid (Front, Left, Top, Isometric, each a few hundred
pixels) — a small feature (a boss, a slot, one dovetail tooth, a vent hole) is hard
to actually inspect at that scale, especially
right after adding or changing it at the user's specific request, when they want
to see that exact change clearly. Generate a standalone, higher-resolution detail
preview for it via `--detail`, in **addition to** (not instead of) the normal
`--preview` overview:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py --preview --preview-dir preview \
    --detail "name=<feature_name>;center=<x>,<y>,<z>;size=<mm>[;section=<axis>=<pos>]"
```

- `name` becomes part of the output filename (`<part_id>_detail_<name>.png`, and
  `<part_id>_section_<axis>_<name>.png` when `section` is given) — pick a short,
  descriptive name (`vent_slot`, `dovetail_west`, `mount_hole`), not a generic one.
- `center`/`size` frame a window roughly 2-4x the feature's own size, centered on
  it — not the whole part's extent — so the feature actually fills the frame at
  the higher `DETAIL_VIEW_SIZE` resolution.
- Add `section=axis=pos` when the feature's internal depth or fit matters (a
  blind hole, a boss inside a cavity, a snap-fit lip): it renders a second file, a
  zoomed cross-section through the same point.
- The extra files land in `previews[1:]` of the JSON result (the main overview
  stays `previews[0]`) — repeat `--detail` for more than one feature in the same
  run.

Display every detail/section file alongside the main overview when reporting the
change back to the user — don't make them squint at the small overview tile for a
feature they specifically asked about.

**Step 4 — Decide**

Handle geometry errors first, then decide what this attempt returns.

1. **Geometry errors present** AND attempt < 3 → fix the script (step 2), re-validate (step 3). The render is unreliable when geometry failed, so skip the review for this attempt. Blocking types include `disconnected_body` (a union that split into separate solids — union or bridge the pieces so they fuse into one component).
2. **`success: true` AND no blocking errors** →
   - **Progressive (inline):** run the full **question-driven visual self-review** per `reference/Visual Review Checklist.md`. Generate the question list from this part's `BUILD_PLAN.json` entry (one per interface, block, and union) plus the universal invariants (single connected body, flat bed face, proportions, shape match, authored orientation). Answer each yes/no **against a specific named view, and cite it**: the 2x2 tile panels for exterior questions, a section file for connectedness and interior questions. If no rendered view shows a question's geometry, render the needed section (`--extra-section`) or detail (`--detail`) **before** answering — an uncitable "yes" is not a pass. The connectedness invariant MUST be answered against a section that crosses the body's junctions, never an exterior panel (which can overlap in projection and read as connected when it is not). Per the checklist's coverage-first rule, also report any other discrepancy noticed, however low-confidence or minor, as an advisory finding (confidence + severity) — it does not fail a question or consume a retry.
     - **Every question answered "yes"** → part done. Record `geometry.bbox`. Display the preview PNG (and the section/detail files it was judged against), and any advisory findings grouped separately under their own heading, not mixed with the checklist. Append `- phase3/part_accepted:<part_id>: progressive review passed` to `build/journal.md` (see `skill/resume.md`). Advance to next part.
     - **Any question answered "no"** AND attempt < 3 → record a `visual_mismatch` finding naming the failed question, the cited view, and the discrepancy, then fix the script (step 2) with a targeted edit driven by that description and re-validate (step 3). Advisory findings from this attempt are not folded into the fix.
   - **Autonomous (builder agent):** this attempt is accepted. Record `geometry.bbox` and the preview/section/detail paths, then return the **Builder return contract** (`status: passed`) without judging the render itself — the **Implementation audit** below, run by a fresh-context agent that never saw the script, is the acceptance bar for an autonomous part.
3. **Attempt 3 exhausted** with remaining geometry errors or an unresolved visual-mismatch finding →
   - **Progressive (inline):** summarize the remaining errors and any visual mismatch to the user directly. Ask conversationally: provide a hint, accept the part as-is, or skip this part.
   - **Autonomous (builder agent):** return the **Builder return contract** with `status: blocked` and an `error_summary` — do not ask the user; the agent has no user channel. Main handles the ask via **Escalation** below.

**Step 5 — Log the attempt (always, before retrying or advancing)**

Append exactly one telemetry record for this attempt to `build/attempts.jsonl`
via the helper (never hand-write the JSONL):

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/telemetry.py" append build/attempts.jsonl \
    --field 'part_id=<part_id>' --field 'attempt=<n>' --field 'outcome=<pass|fail>' \
    --field 'error_types=["<type>", ...]' \
    --field 'visual_review={"passed": <bool>, "failed_question": "<q or null>"}' \
    --field 'prompt_chars=<measured character count of build/<part_id>_prompt_attempt<n>.txt>' --field 'model=<executing model>'
```

- `outcome=pass` only when step 4 accepted the part on this attempt; everything
  else (geometry errors, visual_mismatch, user skip/blocked) is `fail`.
- `error_types` lists the typed errors from the wrapper/gate JSON (empty on pass).
- `visual_review` is the JSON `null` when the review did not run for this attempt
  (e.g. geometry failed first).
- `prompt_chars` is the character count of Step 1's `build/<part_id>_prompt_attempt<n>.txt`,
  computed by reading the file — never typed from memory or estimated. See Step 1's
  "Measuring the render" note.
- `model` names the model that actually executed this attempt — the builder
  agent's own model for an autonomous part, the main session's model for an
  inline (progressive) part. Never write the literal `inline` — read the real
  model identity of the executor making this call.
- Skipping this step loses the measurement baseline every prompt/reference change
  is judged against -- it is part of the loop, not optional bookkeeping.

**Telemetry append safety.** Each `telemetry.py append` call opens the file in append
mode and writes exactly one line; builders run **sequentially** (see Agent routing gate
— no parallel builders in this iteration), so there is at most one writer at a time and
no interleaving risk. This assumption breaks if a future change spawns builders in
parallel — concurrent appends to the same file are not verified safe here and must be
checked (or serialized, e.g. each agent returning its rows for main to append) before
parallelizing.

**Read the render before re-rendering.** The preview tile and its section/detail
files are written to stable per-part names, so the next attempt's render overwrites
them. Complete the visual review of an attempt (examine and cite the tile and every
section/detail file it produced) **before** you re-author and re-render for the next
attempt — never review against a file a later render has already overwritten.

## Builder return contract

When the executor is a builder agent (autonomous part), the last thing it does before
finishing is return this contract as its final message — main parses it and never
ingests any image content, only these fields and the paths inside them:

```json
{
  "part_id": "<part id>",
  "status": "passed | blocked",
  "bbox": {"...": "geometry.bbox from the last successful validate"},
  "preview_paths": ["preview/<part_id>_preview.png", "preview/<part_id>_section_*.png", "..."],
  "attempts": <n>,
  "error_summary": "<remaining errors / visual mismatch, or null on passed>"
}
```

`status: passed` means the part cleared its deterministic checks (lint, wrapper
validation, rendering) — it is **not** final acceptance; the part still owes the
Implementation audit below, which is what actually judges the render. `status: blocked`
means attempt 3 exhausted with unresolved geometry errors or a visual-mismatch finding;
`error_summary` is what main shows the user in Escalation.

## Escalation (blocked builder)

When a builder agent returns `status: blocked`:

1. Main summarizes `error_summary` to the user and asks conversationally: provide a
   hint, accept the part as-is, or skip this part.
2. **Hint** → **resume the same builder agent** (the one already spawned for this part,
   not a new one) with the hint as its next message. The resumed agent keeps its full
   attempt history and context — a cold respawn would discard exactly the memory the
   hint is meant to steer. It continues the write/lint/validate/render loop
   with the hint applied and returns an updated **Builder return contract** when done.
2. **Accept as-is** → treat the last attempt's render as the final result for this part;
   record it and advance. Skip the Implementation audit for this part (the user already
   overrode the bar).
3. **Skip** → advance to the next part without this part's geometry; note the skip in
   the design-approval checkpoint summary.

Whichever outcome, append one line to `build/journal.md` (see `skill/resume.md`) before
moving on:

```
- phase3/escalation:<part_id>: <hint given verbatim | accepted as-is | skipped>
```
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

```
<working directory>/
  README.md, REGENERATE.md, parameters.py, model.3mf, BUILD_PLAN.json, printer_profile.json
  pyproject.toml, .python-version, uv.lock, .venv/
  build/   <part_id>.py (part scripts only), build.py, orientations.json, *.orientation.json, attempts.jsonl, cost.json
  lib/     bundled tooling (below)
  stl/     export_manifest.json, <part_id>.stl, plate_<n>.stl
  preview/ <part_id>_preview.png, _detail_*.png, _section_*.png
```

```bash
# POSIX
cp "$SKILL_DIR/src/build_template.py" build/build.py
mkdir -p lib
for m in mesh_io.py model_export.py print_orientation.py placement.py mate_chain.py units.py freshness.py cq_verify.py cq_compat.py; do
    cp "$SKILL_DIR/src/$m" lib/
done
cp -r "$SKILL_DIR/src/exporters" "$SKILL_DIR/src/blocks" lib/
cp "$SKILL_DIR/src/project_template/pyproject.toml" pyproject.toml
cp "$SKILL_DIR/src/project_template/.python-version" .python-version
uv sync
uv run python build/build.py
```

```powershell
# Windows (PowerShell)
Copy-Item "$SKILL_DIR/src/build_template.py" build/build.py
New-Item -ItemType Directory -Force lib | Out-Null
'mesh_io.py','model_export.py','print_orientation.py','placement.py','mate_chain.py','units.py','freshness.py','cq_verify.py','cq_compat.py' |
    ForEach-Object { Copy-Item "$SKILL_DIR/src/$_" lib/ }
Copy-Item "$SKILL_DIR/src/exporters","$SKILL_DIR/src/blocks" lib/ -Recurse
Copy-Item "$SKILL_DIR/src/project_template/pyproject.toml" pyproject.toml
Copy-Item "$SKILL_DIR/src/project_template/.python-version" .python-version
uv sync
uv run python build/build.py
```

Never copy `build/cost.json` or `build/attempts.jsonl` into `lib/` or the deliverable.
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
Quality gate**, before repeating Phase 4's delivery report. `build/orientations.json`'s
`source_script_hash` stamp (written by the `--source-script` flag above) means a later
standalone `uv run python build/build.py` self-corrects this regardless, but a delivery
report claimed *within this session* must reflect a re-export that actually happened
here, not one left for the user to trigger later. See
[Silica Tray re-export coincidence](TODO.md#silica-tray-re-export-coincidence) for why
this rule exists.
