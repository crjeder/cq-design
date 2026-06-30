## Why

The whole-model-kinematics work made per-union `placement` the structured source of
truth for where each part sits in the assembled model, and `model_export.py` now
positions and emits the assembled model from those placements. But the planning and
assembly prompts still describe the superseded flow: planning emits a required
`assembly` strategy object, and `prompts/assembly.md` instructs the LLM to hand-write
a fused CadQuery script that unions/cuts parts into one `result`. That fused script is
the old positioning mechanism placement replaced -- it has no remaining consumer, and
keeping it contradicts the placement model (two sources of truth for assembled pose).

## What Changes

- **Retire the freeform fused-assembly script.** Remove `prompts/assembly.md`. The
  assembly phase no longer generates a hand-written CadQuery union/cut script; the
  assembled model is produced declaratively from each union's `placement` via
  `model_export.py`. **BREAKING**: the pipeline no longer writes `build/assembly.py`.
- **Drop the `assembly` strategy object from the plan.** Remove the `assembly` object
  (`strategy`/`clearance_mm`/`notes`) and the schema rule requiring it when `parts > 1`.
  Its only consumer was the fused-assembly prompt. Connection intent stays expressible
  through `interfaces`/`blocks_needed` (snap hooks, screw bosses) and `planning_notes`;
  per-mate clearance stays on each `interface.clearance_mm`. **BREAKING**: plans no
  longer carry an `assembly` field.
- **Adapt `prompts/planning.md`.** Remove the assembly-strategy rules and the
  `assembly` block from the output schema/example. State plainly that the model is
  assembled declaratively: parts are positioned with `placement` and the whole model
  is one assembly (fixed set = every other union).
- **Adapt the build pipeline docs (`SKILL.md`).** Replace the "Assembly phase"
  (generate `build/assembly.py` from `prompts/assembly.md`) with a model-export step
  (`model_export.py` from placements). Update the plan summary to drop the
  assembly-strategy line and the quality-gate wiring that fed it `build/assembly.py`.
- **Update validation + tests.** `plan_validate.py` stops requiring `assembly`;
  `test_plan_validate.py` drops the assembly-required test. Clean up `assembly.py`
  references in `quality_gate.py` usage text and `reference-injection`.

## Capabilities

### New Capabilities
- `assembly-phase`: how the build pipeline combines multiple validated parts into the
  final assembled model -- declaratively from per-union `placement` via the model-level
  export, with no hand-written fused CadQuery script.

### Modified Capabilities
- `planning-phase`: the plan schema and planning prompt drop the `assembly` object and
  its multi-part requirement; multi-part assembly is expressed through per-union
  `placement`, and the plan summary no longer shows an assembly-strategy line.
- `reference-injection`: the CadQuery pattern reference is no longer injected into a
  (now removed) `prompts/assembly.md`.

## Impact

- Prompts: `prompts/assembly.md` (removed), `prompts/planning.md` (rewritten assembly
  rules + schema).
- Docs: `SKILL.md` (Phase 3 assembly phase -> model export, plan-summary section,
  quality-gate `<final_script>` wiring).
- Schema/validation: `src/build_plan_schema.json` (remove `assembly` + `if/then`),
  `src/plan_validate.py`, `src/quality_gate.py` (usage examples).
- Tests: `tests/test_plan_validate.py`.
- Depends on the whole-model-kinematics change (per-union `placement`,
  `model_export.py`, `placement.py`) being in place; this change completes the
  transition by removing the flow placement replaced.
