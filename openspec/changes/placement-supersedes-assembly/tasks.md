## 1. Schema and validation

- [ ] 1.1 In `src/build_plan_schema.json`, remove the `assembly` property and the
      trailing `if`/`then` block that requires `assembly` when `parts` has 2+ entries;
      set `additionalProperties: false` behavior so a supplied `assembly` is rejected
      (or document why it is tolerated if the schema is open)
- [ ] 1.2 In `src/plan_validate.py`, delete the check that appends the
      `'assembly' is required when parts has more than one entry` error
- [ ] 1.3 In `tests/test_plan_validate.py`, remove `assembly` from the multi-part
      fixture, delete `test_two_parts_missing_assembly`, and add a test asserting a
      multi-part plan validates with no `assembly` field

## 2. Prompts

- [ ] 2.1 Delete `prompts/assembly.md`
- [ ] 2.2 In `prompts/planning.md`, remove the assembly-strategy rules (the
      "Assembly strategy is required for multi-part models" and
      "Omit the `assembly` key entirely for single-part models" rules), the `assembly`
      block in the output schema example, and the trailing schema note that mentions
      omitting `assembly`
- [ ] 2.3 In `prompts/planning.md`, rewrite the multi-part guidance to state the model
      is assembled declaratively: parts are positioned with `placement`, the whole model
      is one assembly, and connection method is chosen via mating blocks/interfaces
      (keep the existing `placement` and `kinematics` rules intact)
- [ ] 2.4 In `prompts/planning.md`, remove any `assembly.clearance_mm` default language
      and confirm per-mate clearance is described on `interface.clearance_mm`

## 3. Pipeline docs (SKILL.md)

- [ ] 3.1 Replace the Phase 3 "Assembly phase" subsection (generate `build/assembly.py`
      from `prompts/assembly.md`) with a model-export step: run `src/model_export.py`
      from each union's `placement` to produce the named-object 3MF, per-union assembled
      STL, and fused-per-plate STL
- [ ] 3.2 Update the quality-gate description so the multi-part `<final_script>` is each
      union's own part script (per-rigid-body DFM/geometry/overhang), with the
      whole-model kinematic check run once over the exported per-union STLs; remove the
      `build/assembly.py` references
- [ ] 3.3 Remove the "Assembly strategy" line from the plan-summary section and the
      `prompts/assembly.md` row from the "Quick reference: key files" table
- [ ] 3.4 Scrub remaining `assembly`/`build/assembly.py` mentions from SKILL.md that
      describe the fused flow (leave placement/kinematics content unchanged)

## 4. Cleanup of stale references

- [ ] 4.1 In `src/quality_gate.py`, update the module docstring usage examples that
      reference `assembly.py` to a representative part/union script
- [ ] 4.2 Grep the repo for `prompts/assembly.md`, `build/assembly.py`, and plan
      `assembly` field usage; fix or remove any remaining references in docs/CLAUDE.md

## 5. Verify

- [ ] 5.1 Run `uv run pytest tests/test_plan_validate.py` and confirm it passes
- [ ] 5.2 Run `openspec validate "placement-supersedes-assembly" --strict`
- [ ] 5.3 Validate a sample multi-part `BUILD_PLAN.json` (no `assembly` field, parts with
      `placement`) against the updated schema via `src/plan_validate.py`
