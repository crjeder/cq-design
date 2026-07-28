# Design: Engineering Knowledge Elicitation

## Context

Part authoring today is guided by "follow good practice" instructions plus pasted or
cited reference prose (`CadQuery Pattern Reference.md`, FDM guide). The model holds
real engineering knowledge (snap-fit strain formulas, rib-to-wall ratios, boss rules)
but nothing in the pipeline forces it to *derive* anything, so it pattern-matches
instead. IMPROVEMENT_PLAN.md item 5 prescribes a hybrid: elicitation hooks that demand
computed numbers, numbers-demanding review questions, and a thin numeric-only
reference for constants the model cannot recall precisely.

Relevant existing machinery:

- `prompts/part.md` already has a strict "output only the Python script" contract and
  a PARAMETERS/MODEL script skeleton.
- `reference/FDM 3D Print Design Guidelines.md` already uses
  `<!-- applies_to: block1, block2 -->` tag filtering (spec: `reference-injection`),
  with cite-inline / paste-cold rendering modes.
- `reference/Visual Review Checklist.md` is a question bank with universal invariants
  and per-feature generated questions, each answered against a cited view.
- `BUILD_PLAN.json` part entries can declare a `load` (e.g. `load.type: compression`
  with `dir`) and `blocks_needed`.

## Goals / Non-Goals

**Goals:**

- Force derivation: a load-bearing part's script carries a stated load path,
  worst-case stress location, and at least one computed number checked against an
  allowable.
- Make review questions ask for values and thresholds, not judgments.
- Ship a thin numeric reference (constants, coefficients, ratio limits) that plugs
  into the existing tag-filter + cite/paste mechanism unchanged.
- Keep everything measurable with the existing eval harness and telemetry.

**Non-Goals:**

- No FEA, no real structural validation - the rationale is an elicitation device,
  not a verified calculation.
- No Python tooling changes: wrapper JSON contract, `script_lint.py`, and
  `quality_gate.py` are untouched (a lint rule for the rationale block is a possible
  follow-up, not in scope).
- No new eval-harness features; A/B is run with the harness as-is.
- No rewrite of the existing prose references (that is item 14, gated on telemetry).

## Decisions

### 1. The rationale lives as a comment block inside the script

The part prompt demands an `ENGINEERING RATIONALE` comment section between PARAMETERS
and MODEL, not prose before the code.

- Why: `prompts/part.md` ends with "Output only the Python script" - prose before
  code would break the contract for cold-context renders. A comment block survives
  both render modes, travels with the deliverable script, is visible to retry
  prompts (the failed script is re-read), and places the derived numbers next to the
  parameters they justify.
- Alternative considered: a separate rationale field returned alongside the script
  (rejected: changes the author return contract for subagents and `claude -p`, and
  the rationale would be lost once the script is the only artifact on disk).

Format (three required lines for a load-bearing part):

```python
# ============================================================
# ENGINEERING RATIONALE
# ============================================================
# Load path: clip arm bends at its root when the lid is pressed on
# Worst-case stress: arm root, bending at full deflection
# Check: strain = 1.5*t*d/L^2 = 1.5*1.2*1.8/18^2 = 1.0% <= 2.0% allowable (PETG)
```

A part with no load-bearing features writes one line instead:
`# ENGINEERING RATIONALE: no load-bearing features (static cosmetic part)`.

### 2. Applicability is plan-driven, with a stated fallback

The rationale block (full form) is required when the part's plan entry declares a
`load`, or its `blocks_needed`/archetype come from the load-bearing set (snap hooks,
clips, hooks, brackets, screw bosses, pcb standoffs, living hinge, dovetail joints).
Anything else takes the one-line form.

- Why plan-driven: deterministic, checkable from `BUILD_PLAN.json` alone, no
  judgment call in the loop. The one-line form for everything else keeps the habit
  universal (every script has the section) without padding cosmetic parts with
  invented loads.

### 3. Numbers-demanding review rows are a new row class answered against the script, not a view

The Visual Review Checklist gains an "Engineering rows" table, generated (like
per-feature questions) from the same load-bearing trigger set. Each row asks for a
value and its threshold, e.g. "What is rib thickness / wall thickness? Is it
<= 0.6?", "What is the snap-arm strain at full deflection vs. the material
allowable?". Answers cite the script's PARAMETERS / rationale block and the wrapper's
`geometry` JSON - not a rendered view, because these are numeric, not visual,
questions.

- Why bend the "every answer cites a view" rule: that rule exists to stop uncitable
  visual judgments. For numeric rows the analogous discipline is citing the
  parameter or geometry value the number came from; forcing a view citation would
  be theater. The checklist states this distinction explicitly so the two row
  classes don't blur.
- Alternative considered: putting numeric rows in the quality gate instead
  (rejected for now: the gate is deterministic Python and cannot evaluate formula
  plausibility; these rows are for the reviewing Claude).

### 4. `Engineering Design Rules.md` reuses the FDM mechanism verbatim

New `reference/Engineering Design Rules.md`, sections tagged
`<!-- applies_to: ... -->` with the same block-name vocabulary (plus `always` for
material constants). Rendering follows the existing reference-injection contract:
inline renders cite selected section names, cold contexts get the selected bodies.
Content is tables and formulas only: material allowable strains and moduli
(PLA/PETG/ABS/TPU), snap-fit strain formula and coefficients, rib/boss/gusset ratio
limits, heat-set insert and thread-clearance deltas not already in
`hardware_dims.md`. Target under ~4 KB.

- Why reuse: the tag filter, substitution table, and cite/paste split already have a
  spec and an implementation; a second mechanism would be gratuitous.

### 5. A/B is a procedure, not new tooling

Run the eval corpus twice (hooks on vs. the pre-change prompt), compare first-shot
rate, attempts-to-pass, and cost per accepted part from the scorecards. Recorded as a
task, requires no harness changes.

## Risks / Trade-offs

- [Confabulated numbers: the model may write a plausible-looking check with wrong
  arithmetic] -> The numeric review rows re-derive the headline ratio/strain at
  review time; a mismatch is a finding. Imperfect, but strictly better than no
  number at all, and the A/B measures net effect.
- [Prompt growth partially offsets item 13's token savings] -> The rationale
  requirement adds ~15 lines to `part.md`; the new reference is cite-only inline
  and tag-filtered cold, so only load-bearing parts in cold contexts pay for
  section bodies.
- [Trigger-set drift: new load-bearing blocks added later miss the rationale
  requirement] -> The trigger list lives in one place in `prompts/part.md` /
  checklist and names the plan `load` field first, which is block-agnostic.
- [Rationale block could be cargo-culted (copied boilerplate numbers)] -> Numbers
  must reference the script's own parameter names; the review row cross-checks
  against the actual PARAMETERS values.

## Open Questions

- Whether a `script_lint.py` finding for a missing rationale section is worth adding
  (deferred; decide after the A/B shows the hooks earn their keep).
