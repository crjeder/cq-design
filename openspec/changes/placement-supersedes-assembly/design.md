## Context

The whole-model-kinematics change introduced per-union `placement` (a structured pose
in the shared assembled frame) and `model_export.py`, which positions each union by its
placement and emits the assembled model (named-object 3MF, per-union assembled STL, and
fused-per-plate STL). Placement is now the single structured source of truth for where a
part sits in the model.

The freeform fused-assembly flow predates placement:

- `prompts/planning.md` requires an `assembly` object (`strategy`, `clearance_mm`,
  `notes`) for any multi-part plan.
- `prompts/assembly.md` asks the LLM to hand-write a CadQuery script that imports each
  part's `result`, places parts "in their correct relative positions," and unions/cuts
  them into one fused `result` (`build/assembly.py`).
- `SKILL.md` Phase 3 runs that assembly prompt and feeds `build/assembly.py` to the
  quality gate as the multi-part `<final_script>`.

That script is exactly the positioning mechanism placement replaced. Hand-coded
positions in `build/assembly.py` and structured `placement` are two sources of truth for
the same thing, and the fused single body is the wrong subject for the now whole-model,
per-union kinematic check. The `assembly` object's only real consumer was the fused
prompt (strategy/clearance fed the union logic).

This change completes the transition by removing the superseded flow. It assumes the
whole-model-kinematics change (placement, `model_export.py`, `placement.py`) is in place.

## Goals / Non-Goals

**Goals:**
- Remove `prompts/assembly.md` and the hand-written fused-assembly script step.
- Make the assembly phase a declarative model-export step driven by `placement`.
- Remove the `assembly` object and its multi-part requirement from the plan schema,
  planning prompt, and validator.
- Keep the repo coherent: `SKILL.md`, tests, and `quality_gate.py` usage text stop
  referencing `build/assembly.py` / the `assembly` field.

**Non-Goals:**
- Redesigning `model_export.py`, `placement.py`, or `kinematic_check.py` (delivered by
  the whole-model-kinematics change).
- Changing how individual parts are authored or validated in the part loop.
- Changing the kinematic check's semantics (fixed set = every other union) -- only
  removing the fused-script path that fed it the wrong input.
- Adding a new structured field to capture connection method; it stays expressible
  through `interfaces`, `blocks_needed`, and `planning_notes`.

## Decisions

### D1: Remove `prompts/assembly.md` rather than repurpose it
The assembly phase no longer produces LLM-authored code -- positioning is data
(`placement`) consumed by `model_export.py`. There is nothing for an assembly prompt to
generate, so the template is deleted, not rewritten.
- Alternative considered: repurpose the prompt to emit `placement` values. Rejected --
  placement is authored during planning (it is part of the plan), not in a later code
  generation pass. A second prompt would re-introduce a parallel source of truth.

### D2: Remove the `assembly` object entirely (not keep it optional)
The `assembly` object (`strategy`/`clearance_mm`/`notes`) loses its only consumer when
the fused prompt is removed. Connection method (snap vs screw) is already realized
through `interfaces` and `blocks_needed` (e.g. `snap_hook_clip`, `screw_boss`), and
narrated in `planning_notes`/`intent`; per-mate clearance already lives on each
`interface.clearance_mm`. Keeping a now-unconsumed structured field invites drift.
- Alternative considered: keep `assembly` optional as design-intent metadata. Rejected
  -- an optional field with no consumer is dead schema; the prior kinematics proposal
  already set the direction ("the plan SHALL NOT require an explicit assembly grouping").

### D3: Multi-part quality-gating is per union + one whole-model kinematic check
With no fused `build/assembly.py`, the quality gate's `<final_script>` for multi-part
builds is each union's own part script (DFM, geometry, and overhang are per-rigid-body
concerns, and each union is already a validated single-body script). The whole-model
kinematic check runs once over the per-union assembled STLs produced by
`model_export.py`, exactly as the kinematics change specified. `SKILL.md` is updated to
describe: run `model_export.py` after all parts pass, then the kinematic check once;
per-part DFM/overhang is covered by the part loop and per-union gate runs.
- Alternative considered: feed the fused-per-plate STL to the gate via `--stl`.
  Rejected for the general case -- overhang/print-pose analysis is per union, and a
  fused multi-union plate is not the printed rigid body. The fused-per-plate STL remains
  an STL-only export artifact, not the gate subject.

### D4: This change depends on whole-model-kinematics, not vice versa
The deltas here reference `placement` and `model_export.py` as existing. If the two
changes are applied together, apply whole-model-kinematics first. The planning-phase and
reference-injection modifications only remove assembly behavior; they do not redefine
placement (owned by the kinematics change's `printable-unit-model` capability).

## Risks / Trade-offs

- [Connection-method signal is no longer a structured field] -> It is preserved in
  `planning_notes`/`intent` and realized in `interfaces`/`blocks_needed`; the planning
  prompt explicitly instructs the planner to choose mating blocks per the intended
  connection. No automated consumer existed for the structured value.
- [Two pending changes touch overlapping docs/schema] -> Scope is disjoint: kinematics
  *adds* placement/export/kinematics; this change *removes* the fused-assembly flow.
  Apply order documented (D4). Schema edits here only delete `assembly` + its `if/then`.
- [Removing `assembly` is a breaking plan-format change] -> No archived plans are
  consumed by the pipeline; `BUILD_PLAN.json` is regenerated each run. The validator and
  tests are updated in lockstep so no plan can require the removed field.

## Migration Plan

1. Apply whole-model-kinematics first (or together, kinematics first).
2. Remove `prompts/assembly.md`; update `reference-injection` to drop assembly-prompt
   injection.
3. Schema: delete the `assembly` property and the `if parts>=2 then required assembly`
   block; `plan_validate.py`: delete the assembly-required check; `test_plan_validate.py`:
   drop the assembly-required test and `assembly` from fixtures.
4. Rewrite the assembly-related sections of `prompts/planning.md` (rules + schema/example).
5. Update `SKILL.md` Phase 3 (assembly phase -> model export), the plan-summary section,
   and the quality-gate `<final_script>` wiring; scrub `assembly.py` from
   `quality_gate.py` usage text.
6. Run the test suite (`test_plan_validate.py` plus any plan-shape tests).

Rollback: revert the change; the fused-assembly flow and `assembly` field return. No data
migration is required because plans are regenerated, not stored.

## Open Questions

None.
