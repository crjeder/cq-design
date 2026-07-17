# cq-design Improvement Plan

Ordered by impact on result quality, then iteration count, then token cost.
Diagnosis based on: SKILL.md (69 KB), prompts/ (22 KB), reference/ (81 KB),
blocks/inventory.json (34 blocks), TODO.md, occ-error.md.

## Diagnosis

The two reported failure modes — clumsy CadQuery code (repeated OCC / silent-boolean
retries) and wrong shape/topology — share one root cause: **the generation surface is
too open**. Anything the 34 blocks don't cover is authored as raw fluent CadQuery from
a blank file, guarded only by a 37 KB reference dump and a 3-attempt retry loop. The
first geometric truth about a part arrives only after a full CadQuery run; topology is
confirmed beforehand only in words or ASCII art. The pipeline also designs from
scratch even when a proven model already exists online (today's web lookup only
harvests dimensions). And there is **no measurement**: no telemetry on where attempts
fail and no eval harness, so every prompt tweak is unverifiable. Token cost follows
from the same structure — the full SKILL.md (~17k tokens) loads on trigger, and ~10k
tokens of reference are re-substituted into every rendered part prompt even though the
same documents were already read into context once.

---

## P1 — Result quality (first-shot correctness)

### 1. Phase 0: sourcing triage — search before designing

cq-design's proper scope is the case where no usable parametric model exists online.
Add a triage phase ahead of the pipeline with this decision ladder, taking the first
rung that fits:

1. **Found parametric source** (CadQuery, build123d, OpenSCAD, FreeCAD) → reuse or
   convert. build123d → CadQuery is mostly mechanical (both OCC-based); OpenSCAD is
   *not* transpiled — use the .scad as the authoritative topology + parameter source
   and re-author in CadQuery (files with `hull()`/`minkowski()`/recursion don't map
   to BRep). Either way, topology comes from a proven design.
2. **Found STEP/BREP/IGES** → import (`cq.importers`; already on TODO). Yields a dumb
   solid with no feature tree: usable as a mating reference or for boolean
   modification, not reparametrizable. Scope it as exactly that.
3. **Found mesh that fits as-is** → deliver it, but still through `measure_stl.py` +
   the quality gate (found models are frequently wrong or unprintable).
4. **Found mesh that's close** → measure + rebuild the tractable subset only:
   extrusions, revolutions, axis-aligned features that `measure_stl.py` already
   detects. General mesh→parametric reverse engineering is a research problem; do
   not promise it (TODO parks the general case correctly).
5. **Nothing usable** → current pipeline (Phase 1 onward).

**License check is mandatory at rungs 1–4**: ND licenses prohibit exactly the
convert-and-adapt step; record the license and source URL in `planning_notes`.
This does not replace the archetype library (item 2): requests with custom
dimensions and interfaces — the ones cq-design exists for — are the ones generic
downloads fit worst. The two are complementary legs of the ladder.

- Files: SKILL.md new Phase 0 section (reuses the existing Thingiverse/Printables/
  MakerWorld search workflow from Phase 1), `prompts/planning.md` rule for recording
  provenance, small converter helper for build123d sources.
- Acceptance: requests answerable by a found model skip the build loop entirely.

### 2. Part archetype templates (highest leverage for from-scratch parts)

Most from-scratch requests are variations of a dozen shapes: enclosure body, lid
(sliding / snap / screwed), flanged adapter ring, L-bracket with gusset, flat plate
with boss pattern, hook, clip, stand. Add `templates/` of known-good, parametric,
pre-verified CadQuery scripts, one per archetype, each with a documented parameter
block and cq_verify guards already placed. The part loop becomes: match archetype →
copy → edit parameters → modify deltas. Raw-fluent authoring from a blank file
becomes the fallback, not the default.

- Attacks both failure modes at once: topology is inherited from a correct template,
  and OCC-fragile idioms never get re-invented.
- Files: new `templates/*.py`, an `archetypes.json` index (name, use, params),
  part-loop step in SKILL.md ("Step 1.5 — match archetype"), one planning.md rule.
- Acceptance: for requests covered by an archetype, first-shot geometry pass rate
  measurably above the raw-authoring baseline (see item 8).

### 3. Geometry contract before code

For scratch geometry (no block, no archetype), require the script to open with a
construction plan: an ordered list of named stages, each with expected bbox/volume,
asserted during the run. Extend `cq_verify` with
`verify_stage(wp, label, bbox=(..), vol_min=..)` so a wrong topology fails at the
stage that introduced it — with a stage name — instead of surfacing three steps later
as a cryptic OCC error or a failed visual review.

- Files: `src/cq_verify.py`, `prompts/part.md` (require the stage plan), error-type
  table in SKILL.md (`stage_mismatch`).
- Acceptance: retry prompts name the failing stage; average attempts on scratch
  parts drop.

### 4. Move user review earlier — and make frequency a policy

User review catches intent mismatches (the wrong-topology failures); it does nothing
for OCC errors and silent booleans, which belong to the deterministic loop. So the
goal is not *more* review but *earlier* review, where a correction costs seconds
instead of a rebuild:

- **Profile stub render, user-facing by default.** Before authoring the full part,
  generate a ~10-line stub (the part's characteristic 2D profile, extruded), render
  it, and show it to the user for silhouette confirmation. Self-review only in
  autonomous mode.
- **Progressive build as the default mode**, not the complexity-gated exception:
  per-stage checkpoints (base shape → features → finishing) are exactly "review as
  often as possible" at the moments review is cheap.
- **Declared review policy.** Plan-level `review_policy: minimal | checkpoints |
  every_stage` (default `every_stage`), so frequency is a user setting, not a
  hardcoded behavior — the existing autonomous-run override folds into it.

- Files: SKILL.md part loop (Step 0 stub + build-mode gate replaced by
  `review_policy`), `src/build_plan_schema.json` (one field), planning.md rule.

### 5. Engineering knowledge: elicit it, don't just paste it

The model already knows cantilever snap-fit strain formulas, rib-to-wall ratios, and
boss design rules from training; the failure is elicitation reliability. A large
pasted reference is deterministic but gets skimmed — and a 10k-token reference dump
actively suppresses latent-knowledge use by anchoring attention on the pasted text.
Hybrid approach:

- **Elicitation hooks in `prompts/part.md`**: require a short engineering-rationale
  block per part — state the load path, the worst-case stress location, and the
  computed number ("strain at full deflection = …, allowable for PLA = …"). A model
  forced to derive uses what it knows; one told "follow good practice"
  pattern-matches.
- **Numbers-demanding review questions** in the visual/gate checklists ("what is the
  rib thickness / wall ratio? is it ≤ 0.6?") instead of judgment questions.
- **Thin numeric reference** (`reference/Engineering Design Rules.md`, tag-filtered
  like the FDM guide) carrying only what the model cannot recall precisely: material
  constants, insert tables, clearance deltas, formula coefficients. No prose
  tutorials.
- A/B the hooks against the prose via the eval harness (item 8) — this debate is
  settled empirically or not at all.

- Files: `prompts/part.md`, `reference/Engineering Design Rules.md` (new, small),
  Visual Review Checklist rows.

### 6. Fix the known flaky export crash

`occ-error.md` documents a worked-around cq_warehouse `Shape.copy` deepcopy crash
inside `model_export`'s rotations — flaky kernel failures burn retries and erode trust
in every downstream check. Scope the cq_warehouse monkeypatch (import it only where
hardware blocks need it) or pin/patch the dep so `placement.apply_cq` never routes
through the BinTools serialize/deserialize path.

- Files: `src/blocks/hardware.py` (localize import), possibly `pyproject.toml`.
- Acceptance: the two error signatures in occ-error.md no longer reproducible.

---

## P2 — Iteration count

### 7. Static pre-flight lint (cheapest retry killer)

New `src/script_lint.py`: AST-based, no CadQuery import, runs in milliseconds before
the first real run. Mechanically checkable anti-patterns: booleans in a loop, missing
`result`, submodule block imports, `cq.exporters.export` calls, magic numbers outside
PARAMETERS, `.center()`/`.hole()` followed by feature placement without re-anchor,
computed-offset boolean without a `verify_boolean` guard, `.shell()` after
`.fillet()`. Every catch saves a multi-second CadQuery run plus a retry round.

- Files: new `src/script_lint.py` + `tests/test_script_lint.py`; SKILL.md Step 2.5
  ("lint before validate; fix findings before the first run").

### 8. Failure telemetry + eval harness (measurement backbone)

Log every part attempt to `build/attempts.jsonl`: part id, attempt number, error
types, whether visual review failed and on which question, approximate prompt size,
and (once item 15 lands) which model authored the attempt. Add `evals/` with ~10
canonical requests (plan + golden mesh each) and a runner that scores first-shot
success rate, attempts-to-pass, Chamfer distance against the golden mesh, and **cost
per accepted part** (tokens × model price × attempts). Run before/after any prompt,
reference, or model-routing change.

- This is the prerequisite for tuning everything else — items 2, 5, 7, 9, 14, 15
  all claim effects this harness verifies.
- Files: small hook in the SKILL.md part loop (append one JSON line per attempt),
  new `evals/` directory + runner script.

### 9. Typed OCC error triage

`occ_exception` is a catch-all, so its retries are the least targeted. Map the
recurring OCC signatures (BRepAlgoAPI "command not done", fillet/chamfer failures on
short edges, zero-thickness results, the BinTools signatures from item 6) to specific
typed hints in `run_cadquery_model.py`, like the existing `silent_boolean` family.
Feed frequencies from item 8's telemetry.

- Files: `src/run_cadquery_model.py` error mapping + SKILL.md error table rows.

### 10. Collapse redundant review layers

Three overlapping correction loops exist: part-loop visual review (3 attempts), the
design approval checkpoint, and the quality gate's embedded `claude -p` fix rounds
(up to 2). The `claude -p` subprocess is the worst of them — it pays a cold context
to fix findings the orchestrating Claude could fix inline with full planning context.
Make the gate report-only by default (`--no-fix` behavior as default); route its
findings back into the same inline part-loop fix path.

- Files: `src/quality_gate.py` default flip, SKILL.md quality-gate section.
- Also saves tokens (every `claude -p` round is a fresh full-context invocation).

### 11. Restartability: request log + resume state

A crashed or interrupted session is currently unrecoverable except by re-prompting
from memory. Two pieces:

- **Verbatim request log in `BUILD_PLAN.json`** — a `request_log` array holding the
  original user prompt plus every dated clarification/correction, appended, never
  overwritten (the prompt evolves through clarifications; a "current prompt"
  snapshot loses the history that explains the plan). Lives in the JSON, not a
  separate markdown: it travels with the plan, gets schema-validated, and avoids a
  second source of truth drifting.
- **Resume state.** The prompt alone regenerates a *different* build. Resume needs:
  which parts passed (re-validate scripts on disk), attempt counts
  (`build/attempts.jsonl` from item 8), accepted orientations
  (`build/orientations.json`, already exists). Add a SKILL.md resume rule: on
  restart, re-validate the plan from disk, skip parts whose scripts still pass
  validation, continue from the first failure.

- Files: `src/build_plan_schema.json` (`request_log`), planning.md (populate it),
  SKILL.md (append clarifications; resume procedure).

---

## P3 — Token cost

### 12. Split SKILL.md (69 KB → <10 KB core)

SKILL.md is ~17k tokens loaded on every trigger, but most content is phase-local.
Keep in SKILL.md: trigger, phase overview, JSON contract, error table, coordinate
system. Move to per-phase files read only when that phase starts:
`skill/phase0_sourcing.md`, `skill/phase1_requirements.md` (dimension lookup,
Playwright patterns), `skill/phase3_build.md` (part loop detail, progressive build,
orientation loop), `skill/phase4_deliver.md` (export/uv-project scaffolding).
Hardware dimension tables → `reference/hardware_dims.md`, read only when a fastener
block is in play.

- A `/render` or `/deliver` invocation then costs ~2k tokens instead of ~17k.

### 13. Stop re-substituting references into every part prompt

The Phase 3 setup already reads the pattern reference, anti-patterns, and FDM guide
into context once — then the `{{CQ_REFERENCE}}`/`{{FDM_GUIDELINES}}` placeholders
duplicate ~10k tokens into every rendered part prompt (× parts × the prompt's
presence across attempts). Change `prompts/part.md` to cite the already-loaded
documents by name and substitute only the part spec, block specs, and constraints.
Exception: any prompt sent to a cold context — a subprocess or a subagent (item 15)
— still needs full substitution, which is part of item 15's cost equation.

- Files: `prompts/part.md`, SKILL.md Step 1 substitution table.
- Largest single token saving after item 12; zero information loss inline.

### 14. Condense references against measured failures

Once item 8's telemetry shows which reference sections actually correlate with
avoided (or unavoided) failures, cut dead weight from the 24 KB pattern reference and
13 KB anti-patterns file. Archetype templates (item 2) carry the common idioms
implicitly, shrinking what the reference must teach. Target: -40% with no measured
regression on the eval set.

### 15. Per-phase model routing (premium planner, cheaper coder)

Use a top-tier model (e.g. Fable/Opus) for planning and topology decisions — the
high-value, low-volume step — and a cheaper model (e.g. Sonnet) for part-script
authoring — the high-volume step. Two honest caveats before building it:

- **Sequencing.** The reported failure mode lives in the coding step; downgrading
  the coder *before* the scaffolding lands (archetypes item 2, lint item 7,
  condensed references item 14) risks more retries that wipe out the per-token
  saving. The metric is cost per accepted part (item 8), never token price alone.
- **Plumbing reality.** The skill runs inline — the orchestrating Claude cannot
  switch its own model mid-session. The routing mechanism is dispatch to a cold
  context, either a subagent (`.claude/agents/cq-part-author.md` with `model:`
  frontmatter) or `claude -p --model <m>` (the gate already uses this pattern).
  Cold contexts have no ambient references, so the full part prompt must be
  self-contained — partially reversing item 13's saving for those calls. The
  routing wins only when (reference size after item 14) × (cheap price) ×
  (attempts) < (inline authoring at premium price). Measure it, don't assume it.

Implementation:

- Ship `.claude/agents/cq-part-author.md` (part authoring, `model:` set) and
  optionally `cq-planner.md` with the skill; SKILL.md dispatches part authoring to
  the agent when the environment supports subagents, falls back to inline authoring
  otherwise (Cowork vs. Claude Code differ here).
- Configuration: a `models` section in a new `skill_config.json` (per working
  directory, seeded like `printer_profile.json` — model choice is operational, so
  it does not belong in `BUILD_PLAN.json`, and `printer_profile.json` is about
  hardware). Fields: `planner`, `part_author`, `fix_loop`, each a model name or
  `inline`.
- A/B on the eval set (item 8): premium-inline vs. cheap-subagent authoring, scored
  by cost per accepted part and first-shot pass rate.

---

## Suggested sequence

Week 1: items 8 (telemetry/evals — the baseline everything is measured against),
7, 12, 13 — all cheap, immediate wins. Add `request_log` (11) while touching the
schema.
Week 2–3: items 1 and 2 (the sourcing ladder + archetype core), 5, 9, 6.
After that: 3, 4, 10, 14, then 15 once archetypes + condensed references make a
cheaper coder viable — tuned against the eval harness.

Expected end state: requests answerable by a found model never enter the build loop;
archetype-covered parts reach valid geometry in one attempt most of the time; scratch
parts fail with named stages instead of OCC mystery errors; interrupted sessions
resume from the last passing part; and a typical run costs a fraction of today's
tokens (no 17k trigger load, no 10k-per-part reference duplication, no cold
`claude -p` fix rounds, cheap-model authoring where measurement proves it pays).
