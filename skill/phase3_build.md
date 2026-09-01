# Phase 3: Build

Execute the part loop inline. You are the orchestrator.

## Request log

**Appending.** Whenever the user gives a clarification or correction during this phase
(a hint in **Escalation**, a change request at the **Design approval checkpoint**, a
change request during a **Progressive build** stage, or a load correction you announce
during print-orientation optimization), append one entry to `BUILD_PLAN.json`'s
`request_log` array before continuing: `{"ts": "<current UTC ISO-8601>", "kind":
"clarification" | "correction", "text": "<the user's wording, verbatim>", "level":
"functional" | "operation" | "parameter", "targets": ["<part id or part.feature>", ...]}` —
`clarification` for an answer to a question you asked, `correction` for the user
correcting something on their own initiative. `level` is `functional` (adds/removes/
reshapes a part or capability), `operation` (changes how an existing feature is made —
a joint, a cut, a pattern), or `parameter` (a dimension/literal change with the design
otherwise fixed); `targets` names every affected part id and, where the wording is
feature- or parameter-specific, every `part.feature` / parameter name. Append only —
never edit, reorder, or remove an existing entry, even the `initial` one; never
back-fill `level`/`targets` onto an older entry that lacks them.

**Parameter-scope routing.** When you act on an entry with `level: "parameter"`, change
literals only in the part scripts named in that entry's `targets`. A value that must
agree across parts routes through `joints` / `mate_chain.py` (a derived pose or a shared
block parameter) — never by hand-editing the same literal into a sibling part the entry
does not target. (This is the C5 cradle ping-pong: a shared dimension corrected for one
part and duplicated into another keeps re-diverging every round.) If `request_log` is absent from an
older plan, skip this (do not retroactively invent an `initial` entry); if a re-plan
regenerates the file, the planner carries the existing log forward per
`prompts/planning.md` rule 14. When a correction changes a part's design, update that
part's `part_notes` to reflect only the new current state — delete content the
correction supersedes rather than appending a dated round entry or a "SUPERSEDED by
round N" annotation; the round-by-round history lives in `request_log`, not in
`part_notes`.

**Sketches.** If the user attaches an image (a hand-drawn sketch, an annotated
screenshot) to a clarification or correction, copy it into a `sketches/` directory at
the project root before appending the entry, named `<slug>-<ts>.<ext>` (a short slug
from the correction's `text`, or `sketch` if none is obvious; `ts` is the entry's own
timestamp with `:` replaced by `-`). Set the entry's `images` field to the copied
repo-relative path (an array, even for one file).

**Searching.** When you need prior context on a specific decision or feature during
Escalation or a correction round — e.g. recalling why a dimension was corrected earlier
in the build — run `python src/request_log_search.py BUILD_PLAN.json --query <keyword>`
(add `--kind correction`/`--kind clarification`, `--level parameter`, or
`--target <part>` to narrow further) instead of re-reading
`BUILD_PLAN.json`'s full `request_log` array into context. If the matched entry carries
`images`, read the referenced sketch file(s) before re-authoring the part — the same
"read the render before re-rendering" discipline applied to a user-supplied sketch
instead of a generated preview.

**Scoping to a part (for the request-conformance review bar).** Both review paths —
the progressive self-review and the Implementation audit — check the render against
the user's own words as well as the plan. The scoped request text for a part is:
always its `initial` `request_log` entry (it holds the global reference frame), plus
every entry scoped to that part. An entry is scoped to the part when its typed
`targets` name the part (once typed `request_log` entries exist); absent typed
targets, run `request_log_search.py BUILD_PLAN.json --query "<term>"` for the part
id, the part `description`, and each of the part's interface names, and take the
union of the matches. When the plan has no `request_log`, the bar is skipped
entirely.

## Vocabulary

The same rules as `skill/phase2_planning.md`'s Vocabulary section apply to every
user-facing message in this phase (checkpoints, Escalation, fix confirmations):

- Use compass/up-down terms for spatial references; left/right/front/back only when
  directly quoting the user's own words.
- Before acting on a spatial or unagreed feature reference from the user (e.g. "the
  slot on the left"), restate it using the agreed plan name -- and the badge number,
  when the part's callout-annotated preview exists (Step 3 threads one badge per
  named, positioned interface) -- in the same turn you apply the change, e.g.
  "widening `cable_slot` (2)". When the reference plausibly matches more than one
  declared feature, ask which one is meant instead of guessing.

## Setup

Read into context (once, before the loop):

- `BUILD_PLAN.json` — the validated plan
- `$SKILL_DIR/src/blocks/inventory.json` — block metadata (module, function, params)
- `$SKILL_DIR/prompts/part.md` — part prompt template
- `$SKILL_DIR/reference/CadQuery Pattern Reference.md`, `$SKILL_DIR/reference/CadQuery Anti-Patterns.md`, `$SKILL_DIR/reference/emboss_text.md` — read into context once here. This read is the precondition for a progressive part's inline `{{CQ_REFERENCE}}` citation (see the `{{CQ_REFERENCE}}` row below): citation is valid only because these documents are already in the main session's context. An autonomous part's builder agent is a fresh spawn with none of this context, so it still gets the full contents read here re-substituted in full at render time.
- `$SKILL_DIR/reference/FDM 3D Print Design Guidelines.md` — read into context once here, same role for `{{FDM_GUIDELINES}}`
- `$SKILL_DIR/reference/Engineering Design Rules.md` — read into context once here, same role for `{{ENGINEERING_RULES}}`; this read is the precondition for a progressive part's inline citation, same as the FDM guide above
- `$SKILL_DIR/reference/Visual Review Checklist.md` — the visual self-review checklist applied in Step 4

`build/` already exists from `skill/setup.md`'s permission-bootstrap step.

**Precondition for inline citation.** If the part loop starts in a session where these
setup reads are not visible in context (a resumed or compacted session), re-read the
reference documents above before rendering the first inline part prompt — citing a
document that is not actually in context is worse than the duplication this change
removes.

## Build mode (per part)

Decide per part whether to build **autonomously** (the single-shot Part loop below) or
**progressively** (staged, with user checkpoints — see Progressive build). The decision
is driven by the plan's effective `review_policy` (`plan["review_policy"]`, default
`every_stage` when the field is absent):

- **`every_stage`** (default): every part builds progressively, regardless of its
  `interfaces` or `blocks_needed`.
- **`checkpoints`**: build progressively when the part has **at least one `interfaces`
  entry** OR `len(part["blocks_needed"]) >= 3` (the complexity gate); otherwise build
  autonomously. The threshold (`3`) is tunable — adjust it here from field experience.
  This reproduces the pre-`review_policy` default behavior as an explicit opt-in.
- **`minimal`**: every part builds autonomously; no stage checkpoints are shown for any
  part.

**User override:** if the user asks to build progressively (e.g. "show me each step",
"checkpoint as you go") or autonomously (e.g. "just build it", "no checkpoints"), honor
that for the part or the whole run regardless of `review_policy`. Absent an override,
`review_policy` decides.

## Autonomous run discipline (`minimal`)

Applies to the orchestrator and to every builder/auditor agent under
`review_policy: minimal`:

- **Grounded progress.** Before recording an attempt outcome (Step 5) or reporting a
  part as passing, point to the wrapper JSON or check output that shows it. Never
  report a state you have not observed in a tool result this session.
- **No mid-part permission questions.** Proceed on reversible decisions (a coined
  feature name, a clearance within the table, a plate grouping), record the decision in
  the part's `part_notes` or the attempt log, and surface it at the next checkpoint
  rather than pausing to ask. Escalation (a blocked builder) is still a user ask.

## Agent routing gate

Step 0 (the profile-stub review) always runs in the main session, regardless of how the
part's full authoring is routed below — under `checkpoints`/`every_stage` it is a user
checkpoint, and even under `minimal` its self-review is cheap enough not to need a
separate agent spawn. Only Steps 1 onward (full authoring) are subject to this gate.

The build-mode gate above decides progressive vs. autonomous; this gate decides, for an
autonomous part, whether the Part loop below runs inline or inside a spawned builder
agent.

- **Autonomous part → builder agent.** Spawn one Agent-tool call per part, sequentially
  (never in parallel — see Telemetry append safety below). Model override: read
  `models.part_author` from `skill_config.json` in the working directory; if the file or
  key is absent, fall back to mid-tier (Sonnet-class) — a default, not a hard
  requirement — record whatever actually ran in telemetry. If `models.part_author` is
  `"inline"`, do not spawn a builder agent — run the Part loop below in the main session
  instead, exactly like a progressive part's authoring but without per-stage checkpoints.
  The agent's prompt is the Step 1 rendered `prompts/part.md` **plus** the
  Part-loop operating instructions below (Steps 2-5, including the return contract) —
  the agent owns its own write/lint/validate/render loop for up to 3 attempts
  and does not interact with the user. Prepend the cross-part pitfall note (see below)
  when this session has already built a prior part. Main never receives rendered image
  content from the agent — only the paths and the structured return described in
  **Builder return contract**. A part gets at most one builder agent: no additional
  agent is spawned to review, verify, double-check, or re-run its work — the fresh-context
  implementation auditor (below) is the single review agent, and the deterministic checks
  are programs, not agents. A failed attempt or an escalation with a user hint resumes the
  same builder agent rather than spawning a second one for that part.
- **Progressive part → inline, unchanged.** Runs in the main session exactly as
  documented in **Progressive build** below, with its per-stage user checkpoints. Not
  agentified — those checkpoints are user dialog by definition.

## Part loop

Followed by whichever executor owns this part: the **builder agent**, for an autonomous
part (Step 1 is rendered by main before spawning; Steps 2-5 run inside the agent), or the
**main session**, for a progressive part's per-stage authoring (see Progressive build,
which reuses these steps) — every "you" below refers to that executor.

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

**Sections through declared positions — a rule, not a judgement call.** With no
positions, `--cross-sections` cuts X/Y/Z through the bounding-box center only — on a
hollow box, the one place guaranteed to show air. If this part has ANY named+
positioned `interfaces[]` entry, add one `--extra-section axis=value_mm` per selected
entry (repeatable); do not rely on the center-cut fallback. Selection and axis choice:

1. Build the candidate list from the same named+positioned `interfaces[]` entries
   already used for `--callout` above.
2. Match each candidate to a `request_log` entry by `targets` membership: the
   candidate matches an entry when its `name` (or `<part>.<name>`) appears in that
   entry's `targets`. For a `request_log` entry that carries no `targets`, fall back
   to `request_log_search.py BUILD_PLAN.json --query "<name>"` (substring against
   `text`). Note the highest-priority `kind` among the matched entries, if any.
3. Sort into tiers: (1) matched a `kind: clarification` entry, (2) matched a
   `kind: correction` entry, (3) everything else (no match, or only `kind: initial`).
   Within a tier, order matched entries by `request_log` array position descending
   (most recent first); unmatched tier-3 entries keep plan declaration order.
4. Fill the selection from tier 1, then tier 2, then tier 3, stopping at **3** total —
   the fixed cap that keeps preview volume reviewable regardless of interface count.
5. For each selected entry, pick the cut axis normal to its declared `wall` field
   when present (cuts the feature face-on); otherwise use the axis of
   `position_mm`'s largest-magnitude component relative to the part bbox center.

E.g. `--extra-section x=50 --extra-section x=110` for two selected seam tabs at
x=50 and x=110. When `--extra-section` positions are given they replace the center
cuts; each is written as its own `<part>_section_<axis>_<pos>mm.png`. The
bbox-center fallback (no `--extra-section` at all) applies only when the part has
zero named+positioned interfaces — otherwise a disconnection or a feature poking
into a cavity would be invisible from every exterior panel (see `CadQuery Pattern
Reference.md` gotcha 12).

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
   - **Progressive (inline):** run the full **question-driven visual self-review** per `reference/Visual Review Checklist.md`. Generate the question list from this part's `BUILD_PLAN.json` entry (one per interface, block, and union), the request-conformance questions from the scoped `request_log` text (the `initial` entry plus this part's entries — see the Request log section's "Scoping to a part"; skip this class when the plan has no `request_log`), plus the universal invariants (single connected body, flat bed face, proportions, shape match, authored orientation). Answer each yes/no **against a specific named view, and cite it**: the 2x2 tile panels for exterior questions, a section file for connectedness and interior questions. If no rendered view shows a question's geometry, render the needed section (`--extra-section`) or detail (`--detail`) **before** answering — an uncitable "yes" is not a pass. The connectedness invariant MUST be answered against a section that crosses the body's junctions, never an exterior panel (which can overlap in projection and read as connected when it is not). A request-conformance question answered "no" is an **advisory** finding (cite the contradicted request phrase and the view) that does not fail the review or consume a retry, unless the same discrepancy also answers a plan-derived question or universal invariant "no" — then it is a blocking `visual_mismatch` like any other. Per the checklist's coverage-first rule, also report any other discrepancy noticed, however low-confidence or minor, as an advisory finding (confidence + severity) — it does not fail a question or consume a retry.
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

## Implementation audit

Every part a builder agent returns as `status: passed` is judged by a fresh-context
**auditor agent** before it counts as accepted — the deterministic checks the builder
passed are not a review of the render; this audit is the real acceptance bar for an
autonomous part.

1. **Spawn** one auditor agent per accepted part. Its prompt contains: the part's full
   `BUILD_PLAN.json` entry (dimensions, interfaces, blocks_needed, unions), the
   preview/section/detail image paths from the Builder return contract, and the
   **scoped `request_log` text** for the part (the `initial` entry plus the per-part
   entries — see the Request log section's "Scoping to a part"). It does **not**
   receive the part script — adding the request text does not relax that rule; the
   auditor judges the render against the plan's intent *and the user's own words* with
   no chance to rationalize from the code that produced it. When the plan has no
   `request_log`, no request text is passed and the request-conformance bar is skipped.
2. **Checklist.** The auditor applies `reference/Visual Review Checklist.md` exactly as
   Step 4's progressive-mode review would: one question per interface, block, and union,
   the request-conformance questions generated from the scoped `request_log` text
   ("does the render satisfy the user's own words?"), plus the universal invariants
   (single connected body, flat bed face, proportions, shape match, authored
   orientation), each answered against a specific cited view. Per the checklist's
   coverage-first rule, report every discrepancy observed — not just the ones that fail
   a question.
3. **Return contract:**

```json
{
  "part_id": "<part id>",
  "verdict": "pass | fail",
  "failed_questions": [
    {"question": "<checklist question>", "view": "<cited file>", "discrepancy": "<what's wrong>", "confidence": "<low|medium|high>", "severity": "blocking"}
  ],
  "findings": [
    {"question": "<checklist question or observation>", "view": "<cited file>", "discrepancy": "<what's wrong>", "confidence": "<low|medium|high>", "severity": "advisory"}
  ]
}
```

`failed_questions` holds every checklist question answered "no" (`severity: blocking`,
as before). `findings` holds every other observed discrepancy — low-confidence or minor
— each carrying its own `confidence` and `severity: advisory`. An advisory finding does
not fail the audit and is never folded into the fix prompt in step 5 below; it is
reported to the user alongside the accepted part.

A **request-conformance mismatch** (the render contradicts the scoped `request_log`
text) is an advisory `finding` — cite the contradicted request phrase and the view —
and by itself keeps `verdict: pass`, surfaced to the user without resuming the
builder. It becomes a blocking `failed_questions` entry **only** when the same
discrepancy also answers a plan-derived question or universal invariant "no"; in that
case cite the request phrase in that entry as supporting evidence and resume the
builder as normal.
4. **Pass** (`failed_questions` empty) → the part is finally accepted. Append
   `- phase3/part_accepted:<part_id>: implementation audit passed` to
   `build/journal.md` (see `skill/resume.md`). Advance to the next part, surfacing any
   `findings` to the user grouped separately from the review.
5. **Fail** (`failed_questions` non-empty) → **resume the same builder agent** (not the
   auditor, and not a fresh builder) with the named question, cited view, and
   discrepancy as a targeted `visual_mismatch` fix — the builder still has its attempt
   history and script in context. The builder re-enters step 2 for that fix,
   re-validates, and returns an updated contract; re-spawn the auditor on the new
   preview paths. This does not consume one of the builder's original 3 attempts
   against a part that already passed its own loop — treat it as a bounded follow-up
   (one retry) before escalating to the user the same way as **Escalation** above.

## Placement write-back

Once a part is finally accepted — progressive Step 4's "every question yes" path, or the
Implementation audit's pass verdict for an autonomous part — write back the `placement`
the author reported (contract rule 6 of `prompts/part.md`) into that part's entry in
`BUILD_PLAN.json`, replacing any planner-written proposal already there. Same write-back
principle as the `load` correction above: a corrected understanding belongs in the plan,
not just in this one script. Two cases need no write:
- The authored geometry already sits in the pose `pose_intent` describes (or no
  `pose_intent` was declared) — leave `placement` absent, meaning identity.
- The part is reached via a `joints` mate chain — it must never carry its own
  `placement`; its pose is derived.

Announce the write-back to the user only when it replaces a differing proposal (silent
when it confirms an existing value or leaves absence unchanged).

## Cross-part pitfall injection

Before spawning the builder agent for part *k* (k > 1 in this session), scan this
session's `build/attempts.jsonl` for error types that recurred (the same `error_types`
entry across 2+ prior attempts, any part). If any are found, prepend one or two lines to
the rendered part prompt before it becomes the agent's prompt:

```
Known pitfalls this session: <error_type> recurred <n> times (e.g. on <part_id>). <one-line mitigation if obvious from the error's hint>.
```

Keep it to a line or two — this is a cheap nudge, not a report. Skip it entirely when no
error type has recurred, or for the first part of a build (nothing to scan yet).

## Progressive build

Used for a part the Build mode gate (or the user) routed to progressive. Instead of
producing the finished part in one shot, construct it in three ordered stages, pausing
for the user between each. Do not disappear and return with a finished part — show
progress at each stage.

**Stages:** `base shape` → `features` → `finishing`

- **base shape** — outer shell / overall body, no features yet
- **features** — boolean cutouts, bosses, ports, slots, vents, and every `interfaces` entry
- **finishing** — fillets, chamfers, and final cleanup

For each stage, in order:

1. **Author the stage** — write the current `build/<part_id>.py` reflecting everything through this stage (reuse Step 2 authoring rules).
2. **Validate** — run Step 3 (`run_cadquery_model.py --preview --cross-sections`). Fix any geometry errors (the same retry handling as Step 4 item 1) **before** showing the checkpoint, so the user always reviews a geometrically valid stage.
3. **Visual self-review** — apply `reference/Visual Review Checklist.md` scoped to the features expected through this stage (e.g. don't fault a missing port at the base-shape stage). Resolve any `visual_mismatch` before the checkpoint.
4. **Checkpoint** — display the staged preview PNG and a one-line summary of what this stage added, then wait. The user can:
   - **Approve** → advance to the next stage (or complete the part if this was `finishing`).
   - **Request a change** → re-author this stage with the feedback, re-validate (2), re-review (3), present the checkpoint again. When the request names a specific small feature (add a vent here, move this boss, change this dovetail), also generate a `--detail` preview for that exact feature (see Step 3's "Feature detail previews") alongside the staged overview — the user asked about one small thing, so show them that thing at a size they can actually inspect, not just the whole-part tile again.
   - **Skip remaining** → finish the rest of the part with the autonomous Part loop; show no further checkpoints for this part.

**Completion bar:** a progressively built part is done only when its final geometry
satisfies the plan dimensions within tolerance AND passes the **full** visual self-review —
the same bar as the autonomous path. Progressive build does not lower the criteria.

## Design approval checkpoint

Once every part in `plan["parts"]` has passed its part loop and, for autonomous parts,
its Implementation audit (progressive parts pass on their own full Step 4 review), stop
before optimizing print orientation or exporting anything. The auditor's checklist is
Claude checking a render against the plan's own checklist — it is not the user checking
the render against what they actually pictured.
A part can pass that checklist and still be wrong in the user's eyes, and nothing
upstream of this point has asked them to look.

Display every part's final preview PNG together in one message (re-display ones shown
earlier in the loop; don't assume the user still has them in view) and ask directly:

> Here's every part as modeled. Does this match what you had in mind? Reply to
> approve, or describe what to change.

- **Approve** → continue to print-orientation optimization.
- **Request a change** → identify the affected part(s), re-enter that part's loop
  (Step 2 onward) with the user's feedback as a targeted edit, re-validate (Step 3),
  re-review (Step 4), then re-present this checkpoint with the updated renders. If this
  is a later session and the part's script may have been hand-edited outside the skill
  since it was last generated, read its current `PARAMETERS` block before editing --
  treat those values as authoritative over `BUILD_PLAN.json`'s `dimensions`/`part_notes`
  for that part. Update `BUILD_PLAN.json`'s `dimensions` afterward only if the edit
  changes the part's overall envelope.

Skip this checkpoint only when the user has explicitly asked for a fully autonomous
run with no checkpoints (see Build mode override above) — in that case still display
the previews for the record, but proceed straight to print-orientation optimization
without waiting.

Once approved (or skipped per the override above), append one line to
`build/journal.md` (see `skill/resume.md`):

```
- phase3/design_approved: <n> parts
```

## Print-orientation optimization

After every union passes the part loop, choose how each one sits on the bed before
exporting. The objective is **user-selectable** via the plan's `optimize_for` field (a
plan-level default with optional per-part override; defaults to `strength`):

- **`strength`** (default): keep the part's load in the layer plane (FDM is weakest across
  layer lines, build Z), then least support as the tiebreaker.
- **`min_support`**: minimize support material first, strength as the tiebreaker. For jigs,
  drafts, and parts where print time/cleanup matters more than load capacity.
- **`visual_quality`**: best surface appearance first, strength then support as tiebreakers.
  Penalizes gentle inclines (surfaces sloped under 45 deg, which stair-step visibly) and
  rewards orienting the part's cosmetic surface (`show_face`) face-down against the smooth
  bed. For display pieces.

When the user states a priority ("optimize for looks", "minimize supports"), it should
already be recorded as `optimize_for` in `BUILD_PLAN.json` during planning; honor it here.

Run the optimizer once per union, on the union's **authored-frame** STL (the part's own
`result`, before any `placement`), since print orientation is a property of the part, not
of its assembled pose. Export that authored STL first (hidden during the loop), into
`stl/` -- the same directory the deliverable STLs land in below, so nothing scratch ends
up in `build/`; Model export overwrites it there with the real assembled-pose STL once
every part passes -- then optimize with the part's effective mode:

```bash
# authored-frame STL for the part (deliver mode writes it out, into stl/ not build/)
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py --deliver --formats stl --output-dir stl
# orientation: pass the part's load.dir / load.type from the plan (the planner sets
# load on every part per planning rule 10; if a part legitimately has no structural
# load, the plan carries load.type=compression). Omitting --load makes strength
# orientation-neutral (no load axis is guessed). Pass --show-face when declared, else
# it is inferred. --optimize-for is the part's effective mode (default strength).
# --source-script stamps the result with this script's provenance hash, so a later
# edit to build/<part_id>.py is detectable as staleness when build.py reuses this
# entry from orientations.json (see "Artifact freshness" below).
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/print_orientation.py" \
    stl/<part_id>.stl --overhang-max-deg <overhang_max_deg> \
    --optimize-for <strength|min_support|visual_quality> \
    --source-script build/<part_id>.py \
    [--load x,y,z] [--load-type tension|compression|bending|shear] [--show-face x,y,z]
```

Each run prints a JSON result: the active `optimize_for`, a `rotate` transform (placement
convention), the `strength_score`, `support_score`, `bed_contact_mm2`, `visual_score` (with
`cosmetic_down` and `gentle_incline_fraction`), the `load_dir` used (with `load_declared`),
`load_type` used, the `show_face` used (with `show_face_inferred`), and a `rationale`.

**The loop:** read the score breakdown and decide.
- **Sanity-check the load first, before trusting the score.** `strength` mode keeps the
  declared load direction in the layer plane — correct for tension/bending/shear, but
  pointless for a **compression** load (a resting weight pressing straight through the part's
  thickness: a base, plinth, pedestal, foot) and for a non-load-bearing **cover/lid/panel**.
  A compression/cover part scored as tension gets tipped onto its edge chasing an irrelevant
  "strength" goal — check `build_height_mm` and the rotation against physical common sense
  (would you actually print this thin, wide part standing on its edge?), not just the numeric
  score. The optimizer no longer guesses a load: if `load_declared` is false the strength
  score is neutral (support/bed-contact decided) — which is right only if the part truly has
  no load. If the load is really compressive, or the plan's declared `load.dir`/`load.type`
  doesn't match what you now know about the real load path, or the part carries a real load
  that was left undeclared: **write the correction into `BUILD_PLAN.json`'s `load` field for
  that part** (same write-back principle as the printer-profile field write-back in Phase 2 —
  a corrected understanding belongs in the plan, not just in this one CLI invocation),
  announce the correction to the user, then re-run the optimizer with `--load`/`--load-type`
  reflecting the now-declared plan field.
- **Accept** the recommended orientation when its scores are acceptable for the chosen mode,
  or when no better orientation exists at comparable primary score.
- **Improve** the part when the chosen mode's primary score is poor for a load that
  genuinely is tension/bending/shear: make a targeted geometry edit to the part script
  (chamfer a steep overhang or a gentle incline, add a print-in-place foot, split a
  feature), re-validate it (Step 3), and re-run the optimizer. Re-scoring on identical
  input is deterministic, so a changed score reflects the edit.
- Respect the user's mode: `visual_quality` and `min_support` may deliberately accept a
  weaker or higher-support pose. The non-primary scores stay in the result and rationale, so
  if the trade-off looks unacceptable, surface it to the user rather than silently overriding
  the mode.

Collect the accepted orientations into `build/orientations.json` mapping each part id to
its result (`{"<part_id>": {"rotate": [...], ...}}`). This file feeds the model export and
the quality-gate recipe below.

Once every union has an accepted orientation, append one line to `build/journal.md`
(see `skill/resume.md`):

```
- phase3/orientation_chosen: <n> unions, see build/orientations.json
```

## Model export

Before exporting, re-run `plan_validate.py` against `BUILD_PLAN.json` now that every
part's placement write-back (above) is in the plan. This run is authoritative for any
check that consumes `placement`, including the joint-contract axis arm (see
`assembled-pose-handback` design D5) — the Phase 2 run could only report it as a
deferred advisory, since the placements did not exist yet. A failure blocks the export:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json
```

The model is assembled declaratively from each part's `placement` — there is no
hand-written fused-assembly script. Run the model export to emit the deliverables. Pass
`--orientations build/orientations.json` so the **deliverable 3MF/STL are written in each
union's recommended print orientation**; the assembled-pose per-union STLs that the
kinematic check consumes are still written from `placement`, unaffected:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/model_export.py" \
    --plan BUILD_PLAN.json --parts-dir build --out . --stl-out stl \
    --orientations build/orientations.json
```

This writes a named-object `model.3mf` **at the project root** (each union a separately
named object in its print orientation, carrying its `plate` metadata), one
**assembled-pose** STL per union into `stl/` (`stl/<part_id>.stl`, the kinematic check's
input, in `placement` pose), and one fused STL per plate that holds more than one union
into `stl/` (in the plate's print orientation). Run the export even for a single-part
model to get the print-oriented deliverable; omit `--orientations` to fall back to
assembled-pose deliverables.

Then make the working directory a **self-contained uv project** so the user can
regenerate the plates on any machine with uv, without the skill installed. The directory
layout keeps `build/` to only the part scripts you author -- everything else (bundled
tooling, STL, 3MF, previews) lives elsewhere:

```
<working directory>/
  README.md              # project overview + build instructions (Phase 4)
  parameters.py           # sourced real-world measurements (Phase 2, see below)
  model.3mf                # deliverable, print-oriented
  BUILD_PLAN.json
  printer_profile.json
  pyproject.toml, .python-version, uv.lock, .venv/
  build/
    <part_id>.py           # ONLY the part scripts you (Claude) write and edit
    build.py               # re-runnable driver, copied verbatim (not edited)
    orientations.json, *.orientation.json   # build-process bookkeeping
  lib/                     # bundled tooling, copied so the project is skill-free
    mesh_io.py, model_export.py, print_orientation.py, placement.py,
    mate_chain.py, units.py, freshness.py, cq_verify.py, cq_compat.py,
    exporters/, blocks/
  stl/
    export_manifest.json   # provenance stamp per union/zone (see "Artifact freshness")
    <part_id>.stl, plate_<n>.stl
  preview/
    <part_id>_preview.png, <part_id>_detail_*.png, <part_id>_section_*.png
```

Five steps:

1. **Drop in the re-runnable build script.** Copy `$SKILL_DIR/src/build_template.py`
   verbatim to `build/build.py` (no placeholder substitution).

2. **Bundle the tooling into `lib/`** (a sibling of `build/`, not inside it -- `build/`
   holds only edited part scripts): create `lib/` if absent, then copy in the modules
   `mesh_io.py`, `model_export.py`, `print_orientation.py`, `placement.py`,
   `mate_chain.py`, `units.py`, `freshness.py`, `cq_verify.py`, `cq_compat.py` and the
   packages `exporters/` and `blocks/` (copy the whole directories, including their
   `*.json` data files). `cq_verify.py` and `cq_compat.py` are runtime dependencies of
   generated part scripts and `blocks/hardware.py` respectively (the `cq_warehouse`
   compat shim); `freshness.py` is a runtime dependency of `build_template.py` itself
   (the accepted-orientation staleness check) -- omitting any of these breaks the
   standalone project's own `build/build.py` re-run and its mypy check on a fresh
   machine with no `$SKILL_DIR` to fall back on. `build.py` adds `../lib` (relative to
   its own location) to `sys.path` itself, so no further wiring is needed. Re-running
   the skill overwrites `lib/` with the current `src/` versions.

3. **Scaffold the uv project files** at the working-directory root: copy
   `$SKILL_DIR/src/project_template/pyproject.toml` to `pyproject.toml` and
   `$SKILL_DIR/src/project_template/.python-version` to `.python-version`.

4. **Sync and verify.** Run `uv sync` in the working directory to create `.venv` and
   produce a committed `uv.lock`, then verify the build runs in that environment with
   `uv run python build/build.py`.

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

This gives the user a self-contained project where `uv run python build/build.py`
regenerates every plate with its object in print orientation after a manual part edit,
without re-invoking the skill. It reuses `build/orientations.json` when present (so the
plates match the ones just delivered) and recomputes orientations otherwise. `build.py`'s
own defaults already point at the project root / `stl/` for its output, matching this
layout, so no extra flags are needed for a normal re-run.

Once `model.3mf` and the STLs are written and the standalone project verified, append
one line to `build/journal.md` (see `skill/resume.md`):

```
- phase3/model_exported: model.3mf + <n> STL(s) written
```

## Quality gate

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/quality_gate.py" \
    --script build/<part_id>.py --plan BUILD_PLAN.json \
    --stl-dir stl --orientation build/<part_id>.orientation.json
```

DFM, geometry, and overhang are per-rigid-body concerns, so the gate runs on each
union's own part script: run it once per union for a multi-part model. Pass `--stl-dir
stl` so the kinematic/plate-clearance sweep finds every union's assembled STL there
(it defaults to alongside `--script`, i.e. `build/`, which no longer holds any STLs).
Pass the union's own orientation result (one object split out of
`build/orientations.json`) via `--orientation` so the emitted print recipe's
`orientation` field carries the computed rotation and rationale instead of the default
`flat_bottom_down`. The whole-model kinematic check runs once over the per-union
assembled STLs produced by the model export.

Parse `build/quality_gate.json`. The gate is report-only (`--fix` is not passed) --
it never rewrites the script itself. On a `severity: error` finding, re-enter Step 2's
fix path for the offending part's script, using the finding's `type`, `message`, and
`hint` as the correction, exactly as with a wrapper error from an earlier attempt --
this keeps the fix inside the orchestrating session, with the plan, renders, and
attempt history already in context, instead of a cold `claude -p` subprocess that has
none of it. Re-run the gate after the fix. Bound gate-driven fix rounds at 2 per part;
if `severity: error` findings remain after that, stop and summarize them to the user
rather than retrying further. `severity: warning` findings do not trigger a fix round --
surface them alongside the print recipe. (`--fix` restores the old cold-context fixer
for standalone use outside this pipeline; the skill does not pass it.) Once the gate
passes (or its remaining findings are escalated), append one line to
`build/journal.md` (see `skill/resume.md`):

```
- phase3/gate_result: <pass|escalated>, <n> remaining findings
```

Then proceed to Phase 4.

The gate runs entirely in-process (trimesh + numpy geometry and overhang analysis); it needs no slicer or MCP. Real slicer-based printability validation (e.g. the orca-check MCP) is optional and external, not part of the gate.

If the plan has a `kinematics` array, the gate also runs the **kinematic range check** (`src/kinematic_check.py`) once, after the geometry checks. The sweep is whole-model, so it needs **every union's assembled STL** present in `--stl-dir` (`stl/`) as `<part_id>.stl`. Produce these with the **model export** (`src/model_export.py`), which applies each part's `placement` and writes one assembled STL per union (plus the named-object `model.3mf` and any fused-per-plate STL). The stage degrades to a `check_skipped` warning when a union STL or the `python-fcl`/`scipy` backend is missing. See **Kinematic validation** below.

Whenever any plate carries more than one union (print-in-place), the gate also runs the **plate-clearance check** (`src/plate_clearance_check.py`) once, over the same assembled per-union STLs. For every co-plated union pair it measures the minimum surface-to-surface gap and flags any pair within one layer height (`nozzle_mm * 0.5`) as a `plate_clearance` **error** -- those unions fuse on the bed. The gate runs this automatically (no separate command); it degrades to a `check_skipped` warning when trimesh or the `python-fcl` backend is missing. Measuring on the assembled STLs is valid because a plate fuses as a rigid cluster, so its print-orientation rotation preserves the pairwise gaps.

### Artifact freshness

The kinematic, plate-clearance, and keep-out-zone stages all validate exported STLs against
a part script they were built from -- but none of them re-derive the STL themselves, so
none of them can tell on their own whether the export is still current. `model_export.py`
writes `stl/export_manifest.json` on every run, recording each union's (and keep-out zone's)
provenance stamp (a hash of its source part script). Each of the three stages compares that
stamp against the current `build/<part_id>.py` and, on a mismatch, emits a `stale_artifact`
**error** naming the affected union or zone instead of validating (and possibly passing)
geometry the project no longer builds. **To clear it:** re-run the model export
(`src/model_export.py`, or `build/build.py`) so the STL and its manifest entry reflect the
edited script, then re-run the gate. The same mechanism protects `build/orientations.json`:
`build_template.resolve_orientations` (what `build/build.py` calls) recomputes an accepted
orientation whose stamp no longer matches its script, rather than reusing a pose picked for
superseded geometry, and reports which unions it recomputed in its summary output. A project
exported before this mechanism existed (no manifest, unstamped orientation entries) degrades
to a `check_skipped` warning / unconditional reuse -- never a hard failure.

The gate also runs the **edge-treatment check** (`src/edge_treatment_check.py`) once on the part script, enforcing the reference's Chamfer / Fillet rule (horizontal edge -> chamfer, vertical edge -> fillet). It wraps `cq.Workplane.fillet`/`.chamfer` and re-runs the script to record the exact direction of every treated edge, then classifies each **in the print frame** -- the bed-relative frame where the rule matters -- by rotating its authored-frame tangent through the union's print orientation. Supply that orientation (pass `--orientation`, or keep `build/orientations.json` next to the script); a treated union with no available orientation is reported as `check_skipped` rather than judged in the authored frame. A fillet on a horizontal edge or a chamfer on a vertical edge is an advisory `edge_treatment` **warning** (not blocking -- it is a print-quality preference; the harmful case of a bottom-edge fillet is already caught by the overhang check); diagonal edges and tilted round rims are passed silently. Treat these warnings as suggestions and disregard any that fall on an internal or intentionally-treated edge.

For a part whose effective `optimize_for` is `visual_quality`, the gate also runs the **cosmetic-slope check** once. Shallow UP-facing surfaces (inclined ~5-45 degrees from horizontal) print as visible layer stair-steps. `print_orientation.py` already measures this at the chosen pose (`cosmetic_slope_area_mm2` in the orientation result, up-facing faces only so it does not overlap the overhang check); the gate reads that value from `--orientation` and emits an advisory `cosmetic_slope` **warning** when the area is non-trivial. It is never an error (a shallow ramp still prints) and never fires for non-`visual_quality` parts (a hidden structural slope is fine); with no orientation available it degrades to `check_skipped`. Remedy per the FDM "Cosmetic Slopes" guideline: reshape to >= 45 degrees / vertical, chamfer-step, or lower layer height for the 20-45 degree range -- the optimizer already picked the least-stepping orientation, so rotation alone will not remove it.

The `build/` directory is in your current working directory (the directory you called the skill from), not inside `$SKILL_DIR`.

## Block library

Select blocks in `blocks_needed` during planning. When generating part scripts, write a flat `from blocks import <function>` at the top for each block (see generated-script rules in the core SKILL.md).

### Primitives (`src/blocks/primitives.py`)

| Block | Use |
|-------|-----|
| `fillet_box` | Rectangular solid with filleted vertical edges. Outer shell for enclosures and bases. |
| `hollow_box` | Open-top hollow body via boolean subtraction. Electronics cases, trays, bins. |

### Fasteners (`src/blocks/fasteners.py`)

| Block | Use |
|-------|-----|
| `screw_boss` | Solid cylinder boss with through-hole for M2-M4 self-tapping screws. |
| `pcb_standoff` | Hollow cylindrical standoff for PCB mounting (M2 / M2.5 / M3). |
| `snap_hook_clip` | Cantilever snap-fit hook clip for lid-to-body connections. Union onto lid inner wall. |
| `snap_socket_receiver` | Slot to subtract from a wall to receive `snap_hook_clip`. |
| `alignment_pin` | Tapered cylinder pin for press-fit part registration. |
| `alignment_socket` | Receiving hole for `alignment_pin`. Use `clearance=0.2` for loose, `0.05` for press. |

### Connectors (`src/blocks/connectors.py`)

| Block | Use |
|-------|-----|
| `port_cutout` | Rectangular port opening: USB-C (9x3.5 mm), USB-A (12x6 mm), barrel jack, HDMI, etc. Add 0.3-0.5 mm clearance. |
| `cable_slot` | Elongated slot for cable routing, strain relief, wire management. |
| `vent_grid` | Regular grid of ventilation slots. Subtract from a wall or lid face. |

### Joints (`src/blocks/joints.py`)

| Block | Use |
|-------|-----|
| `dovetail_groove` | Dovetail slot cut into a body top edge for a sliding lid. Subtract from the body. |
| `dovetail_tongue` | Sliding lid panel that mates with `dovetail_groove`. The tongue IS the lid. |

### Gridfinity (`src/blocks/gridfinity.py`)

**Read `reference/gridfinity.md` in full before authoring any part that uses these** --
the grid pitch, foot profile, and stacking clearances are a published standard, and a part
that misses them by a millimetre fits nothing. Never re-derive the profile by hand.

| Block | Use |
|-------|-----|
| `gridfinity_bin` | Complete bin: feet, walls, cavity, stacking lip, plus optional dividers, label shelf, scoop, and magnet/screw pockets. `solid=True` gives a blank to cut custom tool pockets into. |
| `gridfinity_baseplate` | Complete baseplate: a grid of sockets bins drop into, tiling on the 42 mm pitch. |
| `gridfinity_feet` | Just the feet, to union under a custom body (which starts at Z = 4.75) so that body docks into a grid. |
| `gridfinity_socket_cutter` | Just the sockets, to cut into a custom plate, drawer bottom, or tool-wall panel. |
| `gridfinity_dimensions` / `gridfinity_units_for` | The numbers without geometry: a bin's outer size for the plan, or the smallest bin in units that holds an object. |

The `gridfinity-bin` and `gridfinity-baseplate` archetypes (Step 1.5) wrap the first two
directly; match them for any request naming Gridfinity. A part built on these blocks is
checked against the standard automatically by the quality gate (`src/gridfinity_check.py`,
auto-scoped to scripts that use a Gridfinity block); to run it on its own:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/gridfinity_check.py" \
    --script build/<part_id>.py
```

Its `gridfinity_footprint` / `gridfinity_height` / `gridfinity_base_profile` /
`gridfinity_mate` errors name the exact dimension that is off and by how much; treat them
like the wrapper's typed errors (fix the parameter, re-run).

## Kinematic validation

For an assembly whose parts are meant to move relative to each other (a hinge that
folds, a slide that travels, a ball joint that articulates), declare the required
range of motion so the quality gate can verify the parts actually clear that range
without binding. The check is **multi-part only** (it compares separate part STLs):
single-body print-in-place hinges (`pin_hinge`, print-in-place `hinge_leaf`) declare
a revolute `dof` for their nominal motion but are not swept while fused into one body.
The `living_hinge` flexure is a true exception - it has no axle, so it carries no `dof`.

Two pieces declare the motion:

**1. Inventory `dof`** (intrinsic to the joint block, already set in `inventory.json`):

```json
"dof": {"type": "revolute", "axis": "Y", "mechanical_limit": [0, 180], "unit": "deg"}
```

`type` is `revolute` | `prismatic` | `spherical`; `unit` is `deg` (revolute/spherical)
or `mm` (prismatic). `mechanical_limit` is the block's *nominal* full range -- a
sanity bound only. The collision sweep is authoritative for what the printed
instance actually achieves.

**2. Plan `kinematics`** (the range THIS design requires) -- a top-level array in
`BUILD_PLAN.json`:

```json
"kinematics": [{
  "joint_id": "phone_hinge",
  "moving_union": "arm",
  "block": "hinge_leaf",
  "axis_origin_mm": [0, 0, 4],
  "axis_dir": "Y",
  "type": "revolute",
  "required_range": [0, 90],
  "lo_inclusive": true,
  "hi_inclusive": true,
  "unit": "deg",
  "step": 5
}]
```

`axis_origin_mm` + `axis_dir` give the assembled-frame joint axis (you declare it; it
is not inferred). `moving_union` is the part that moves; **the fixed set is every
other union in the model**, so the sweep is whole-model and catches in-context binding
(a lid blocked by the body, not just the hinge in isolation). `required_range` is the
arc the design depends on, **relative to the union's authored pose (zero)**; it may be
negative or straddle zero (e.g. `[-30, 90]`), and `lo_inclusive`/`hi_inclusive`
(default `true`) mark whether each bound must be cleared. `plan_validate.py` checks
`moving_union` exists, the block exists and carries a `dof`, and `unit` matches the
block `dof.unit`.

When describing this range to the user (checkpoint prose, not the JSON), state it as
a clock position on the view whose sight-line is `axis_dir` -- above<->Z, South<->Y,
West<->X -- e.g. "swings to the 90° position in the above view". Never say
"clockwise"/"counterclockwise": right-hand-rule-positive `required_range` reads
clockwise on South/West but counterclockwise on above, so a bare direction word has
no axis-independent correct sign (see `feature-vocabulary` spec).

The gate then performs two checks per joint: (1) `required_range` within a mechanical
limit -- the block's `mechanical_limit` when the entry names one, otherwise the
entry's own `mechanical_limit` when declared -- -> `range_exceeds_limit` on failure
(no mesh loaded); (2) a collision sweep of the moving union against every other union,
each added as a separately named collision object -> `motion_collision` carrying the
binding value and the `colliding_union` so the design loop knows what to fix. A
print-in-place joint (several unions on one plate) is swept the same way -- no special
case. Designed surface contact at the joint is tolerated -- interference is measured as
boolean intersection **volume** against a small `--penetration-tol-mm3` budget, so a
flush resting face measures ~0 and never binds. The check reads the assembled per-union
STLs from the model export (see **Model export** / `model_export.py`).

The sweep travels **outward from the authored pose** (zero), so `[-90, 0]` starts at 0
and moves toward -90, and a range straddling zero is swept as two independent arms. A
cut-short sweep tells you how far the joint got: `achieved_range` (one bound per
direction), `min_clearance_mm`, and `overlap_mm3`, with the stop bisected so it is not
snapped to a `step` sample.

**Contact-limited joints (`stop_on_contact`).** A joint whose travel ENDS by resting
against another body -- a folding leaf closing onto its plate, a lid onto its rim --
can never pass a plain range check: the poses past its stop necessarily interpenetrate
even though the mechanism cannot reach them. Set `stop_on_contact: true` on such an
entry. First real contact is then reported as the joint's mechanical stop: a
`contact_limited_stop` **warning** naming the achieved range and what it stopped
against, not a `motion_collision` error. Declare the ideal travel in `required_range`
anyway -- the warning states the shortfall so you (or the user) can judge whether the
natural stop is the intended rest position. If it is, narrow `required_range` to match;
if not, relieve the contacting feature.

**Block-less (directly-declared) joints.** A custom hinge built from raw primitives
usually has no matching inventory block -- `block` is optional for exactly this case.
Omit it and declare the axis directly; the sweep needs nothing from a block:

```json
"kinematics": [{
  "joint_id": "phone_hinge",
  "moving_union": "arm",
  "axis_origin_mm": [0, 0, 4],
  "axis_dir": "Y",
  "type": "revolute",
  "required_range": [0, 90],
  "mechanical_limit": [0, 180],
  "step": 5
}]
```

`mechanical_limit` is optional too -- declare it for a numeric sanity bound, or omit
it and get a `range_check_not_applicable` warning (not a silent skip) while the
collision sweep still runs. Do not omit the whole `kinematics` entry just because no
block fits: the C5 Phone-Holder retrospective did exactly that for a raw-primitive
clevis/tongue hinge, and the result was seven rounds of a hand-written, unreliable
ad-hoc sweep standing in for what `kinematic_check.py` already does.
