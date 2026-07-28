# Engineering Knowledge: Elicit It, Don't Just Paste It

## Why

The model already knows cantilever snap-fit strain formulas, rib-to-wall ratios, and
boss design rules from training, but the pipeline never forces it to use them: parts
are authored under a "follow good practice" instruction plus a large pasted reference,
which gets skimmed and pattern-matched rather than applied. The result is parts that
pass geometry validation but embody weak engineering (over-strained snap arms,
sink-prone ribs, undersized bosses). Item 5 of IMPROVEMENT_PLAN.md: replace passive
reference-pasting with active elicitation, keeping only a thin numeric reference for
what the model cannot recall precisely.

## What Changes

- `prompts/part.md` gains a required **engineering-rationale block**: before the
  script, the author states the load path, the worst-case stress location, and at
  least one computed number with its allowable (e.g. "strain at full deflection =
  2.1%, allowable for PLA = 4%") for load-bearing features. Parts with no
  load-bearing features state that explicitly instead.
- The **Visual Review Checklist** gains numbers-demanding rows: questions that ask
  for the actual measured/derived value and its threshold ("what is the rib
  thickness / wall ratio? is it <= 0.6?") instead of judgment questions ("do the
  ribs look reasonable?").
- New thin numeric reference `reference/Engineering Design Rules.md`, tag-filtered
  with the same `<!-- applies_to: ... -->` mechanism as the FDM guide: material
  constants, insert tables, clearance deltas, formula coefficients only. No prose
  tutorials.
- The rationale hooks are A/B-testable against prose-reference authoring via the
  existing eval harness (`evals/run_evals.py`, item 8); telemetry
  (`build/attempts.jsonl`) already records per-attempt outcomes to score against.

## Capabilities

### New Capabilities

- `engineering-rationale`: the per-part engineering-rationale block requirement in
  the part prompt (load path, worst-case stress location, computed number vs.
  allowable), including when it applies and how it is carried through retries.

### Modified Capabilities

- `visual-self-review`: the question bank gains numbers-demanding engineering rows
  (value + threshold answers) generated for parts whose plan declares load-bearing
  or ratio-governed features.
- `reference-injection`: a new tag-filtered reference file
  (`reference/Engineering Design Rules.md`) joins the injection/citation contract,
  selected by `blocks_needed`/feature tags like the FDM guide, cited inline and
  injected in full for cold contexts.

## Impact

- `prompts/part.md`: new rationale-block section (both inline and cold-context
  renders).
- `reference/Visual Review Checklist.md`: new numbers-demanding question rows.
- `reference/Engineering Design Rules.md`: new, small, tag-filtered.
- `skill/phase3_build.md`: Step 1 substitution table row for the new reference;
  part-loop note that the rationale block precedes the script.
- No Python tool changes: the wrapper JSON contract, lint, and gate are untouched.
  Eval harness and telemetry are consumers, not modified.
