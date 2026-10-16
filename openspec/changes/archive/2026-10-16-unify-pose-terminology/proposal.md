## Why

`SKILL.md` and the prompt-rendered builder/planner text (`prompts/part.md`, `prompts/planning.md`, `prompts/audit.md`) call the three coordinate states "part frame / assembled frame / print frame". `CLAUDE.md` calls them "build pose / assembly pose / print pose". Source docstrings add a fourth and fifth spelling ("authored frame", "build frame"), and "build frame" is used in two senses (the authored frame in `CLAUDE.md`, the print-oriented frame in `edge_treatment_check.py` / `quality_gate.py`). Builders receive the prompt wording, so they and the maintainers read different vocabularies for the same concepts. `CLAUDE.md`'s "pose" wording is the chosen standard.

## What Changes

- One vocabulary everywhere: **build pose** (frame a part script is authored in; was "part frame" / "authored frame" / "build frame" in the authored sense), **assembly pose** (build pose plus `placement`; was "assembled frame"), **print pose** (build pose rotated by the accepted orientation `rotate`; was "print frame" / "build frame" in the print sense).
- Rewrite prose in `SKILL.md`, `README.md`, `FILES.md`, `ARCHITECTURE.md`, `prompts/*.md`, `skill/*.md`, `reference/*.md`, `commands/*`, and the `description` strings in `src/build_plan_schema.json`, `src/blocks/inventory.json`, plus docstrings, comments, CLI help and user-facing messages in `src/**`.
- Update the matching requirement text in `openspec/specs/**`.
- Add a short glossary to `SKILL.md` and `CLAUDE.md` pointing at one definition.
- Not changed: JSON keys, CLI flags, function names, typed error names, file names (including `src/blocks/print_frame.py` and `print_up()`), the `coordinate_frame` plan field (a compass-to-axis binding, unrelated), and generic uses of "frame" (e.g. "coordinate frame", animation frames). No behavior change.

## Capabilities

### New Capabilities
- `pose-terminology`: the three-pose vocabulary (build / assembly / print pose) as the single canonical naming across docs, prompts, schema descriptions, and user-facing tool messages, with the retired terms banned from them.

### Modified Capabilities
<!-- Wording-only edits to existing specs; no requirement behavior changes, so no delta files. Specs are re-worded in place by the tasks. -->

## Impact

- Docs/prompts: `SKILL.md`, `CLAUDE.md`, `README.md`, `FILES.md`, `prompts/{part,planning,audit}.md`, `skill/*.md`, `reference/scripts.md`.
- Code (text only): `src/{edge_treatment_check,quality_gate,print_orientation,fem_check,plan,write_assembly,placement,mate_chain,preview,run_cadquery_model,feature_presence_check,minimal_cutout_search,print_finishing,keep_out_check,deliverables,build_template}.py`, `src/blocks/{connectors,fasteners,print_frame}.py`, `src/blocks/inventory.json`, `src/build_plan_schema.json`.
- Tests: any test asserting on a changed message string (`tests/test_edge_treatment_check.py`, `test_quality_gate.py`, `test_plan.py`, `test_fem_check.py`); `tests/fixtures/rim_fillet_fins.py.txt` comment.
- Specs: ~20 files under `openspec/specs/` (reworded in place); archived changes and `documentation/DONE.md` are history and stay untouched.
- Risk: the schema `description` strings and `inventory.json` text are rendered into builder prompts, so wording changes alter prompt text (intended).
