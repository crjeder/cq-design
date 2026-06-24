## 1. Plan schema: load hint

- [x] 1.1 Add an optional per-part `load` field to `src/build_plan_schema.json` (a direction in the part's authored frame; e.g. `{"dir": [x, y, z]}` or axis enum, `additionalProperties` false)
- [x] 1.2 Validate the `load` field in `src/plan_validate.py` (shape/normalization), accepting parts that omit it
- [x] 1.3 Add a planning-phase test in `tests/test_plan_validate.py`: plan with `load` validates; plan without `load` still validates
- [x] 1.4 Note the `load` hint in `prompts/planning.md` and the plan summary table in `SKILL.md`

## 2. Orientation scoring tool (`src/print_orientation.py`)

- [x] 2.1 Implement candidate enumeration: convex-hull resting facets + 6 axis-aligned faces, each as the rotation mapping the bed-down normal to -Z; dedupe normals within an angular tolerance
- [x] 2.2 Implement the strength score: transform the load direction by the candidate rotation, score `1 - |load . Z|` (in-plane = high); infer principal load axis from geometry when `load` is absent and report the inferred direction
- [x] 2.3 Implement the support score: reuse the downward-face / overhang-area computation from `quality_gate._analyze_stl` (extract to a shared helper) at the candidate pose vs `overhang_max_deg`; add bed-contact area as a secondary nudge
- [x] 2.4 Implement lexicographic selection: best strength, ties within a tolerance band broken by lowest support
- [x] 2.5 Emit per-union result: rotation transform (placement.py rotation convention) + strength score + support score + rationale; ensure determinism (stable sort, fixed tolerances)
- [x] 2.6 Add a CLI entry point that reads a union STL + plan constraints + optional load and prints the result JSON

## 3. Model export applies print orientation

- [x] 3.1 Extend `export_model` in `src/model_export.py` to accept a per-union print-orientation transform and write each 3MF object's geometry in that orientation (fall back to assembled pose when absent)
- [x] 3.2 Keep per-union assembled-pose STLs (kinematic-check input) written from `placement`, unaffected by print orientation
- [x] 3.3 For multi-union plates, apply the first union's print orientation to the fused STL (per design Open Questions scope)
- [x] 3.4 Thread the print orientations through `main()` (e.g. read an orientations JSON produced by `print_orientation.py`)

## 4. Quality gate recipe

- [x] 4.1 Replace the hardcoded `"orientation": "flat_bottom_down"` in `_emit_print_recipe` with the computed orientation (axis/angle description + rationale) when available
- [x] 4.2 Fall back to the prior constant when no orientation result is supplied

## 5. Pipeline wiring (SKILL.md)

- [x] 5.1 Add the optimization phase between "Model export" and "Quality gate": run `print_orientation.py` per union, read the score breakdown
- [x] 5.2 Document the bounded LLM loop: accept top orientation, or apply a targeted geometry tweak to cut support and re-score
- [x] 5.3 Document that deliverables are exported in the recommended print orientation while kinematic meshes stay in assembled pose

## 6. Tests

- [x] 6.1 `tests/test_print_orientation.py`: in-plane load scores higher strength than across-layer load
- [x] 6.2 Support score increases with exposed overhang area at a candidate pose
- [x] 6.3 Lexicographic selection: strength wins outside the tolerance band; support breaks ties inside it
- [x] 6.4 Determinism: identical input yields identical recommendation
- [x] 6.5 `tests/test_model_export.py`: deliverable written in print orientation; assembled-pose per-union STL unchanged
- [x] 6.6 Run `ruff check --fix` and `ruff format` on all changed Python files; run the full `uv run pytest tests/` suite
