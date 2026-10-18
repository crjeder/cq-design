## Why

Phase 3 gives the same post-acceptance work to two owners, and templates its per-union steps with the wrong id:

- `prompts/part.md:106-156` tells the builder to run `fem_check.py <part>.step` and `toolpath_speed.py --script {{PART_ID}}.py` (no `build/` prefix) "once the script is accepted". `skill/phase3_build.md:169-238` gives the orchestrator the same two steps after acceptance. The builder "own[s] `build/{{PART_ID}}.py` ... and nothing else" (`prompts/builder.md:1-2`), has no way to produce a STEP file (`render_prompt.py:131-154`'s `validate_args` never passes `--deliver`), and is never told when acceptance happens. Its copy of the instructions can only fail or run on the wrong path.
- Print orientation and the quality gate run "per union" (`skill/phase3_build.md:242`, `:282`, `:334`), but every command names `stl/<part_id>.stl` and `build/<part_id>.orientation.json`. A multi-union part's `result` is a dict, and the exporter writes one `<union_id>.stl` per key (`reference/scripts.md:16`, `src/exporters/__init__.py:147-151`), so `stl/<part_id>.stl` does not exist for any part built on `pin_hinge`, which `prompts/part.md:35` requires for every print-in-place hinge.

## What Changes

- Remove the FEM stress advisor run instructions and the whole "Toolpath-speed advisor" section from `prompts/part.md`. Keep one line in the Engineering rationale section: when the orchestrator supplies a FEM result for this part, its failure index and location replace the closed-form `check`/`worst_case_stress`.
- In `skill/phase3_build.md`, template every per-union path with `<union_id>`: the `print_orientation.py` STL input, the `toolpath_speed.py --stl`/`--emit-candidates` input and its `speed_candidates.json` output, the per-union `orientation.json` written after acceptance, the `--print-rotate` hint, the `write_assembly.py` output description, and the quality gate's `--orientation`. Script paths (`build/<part_id>.py`) stay part-keyed.
- State once, at the top of Print-orientation optimization, that a single-union part's union id equals its part id, so the commands read the same as today for every part without `unions`.
- Key `build/orientations.json` by union id, matching `quality_gate.py`'s `_read_orientations` docstring and the existing note that a multi-union part's orientation is keyed by union id.

## Capabilities

### New Capabilities

### Modified Capabilities
- `subagent-orchestration`: adds a requirement that post-acceptance advisors (FEM, toolpath speed) are run by the orchestrator only, never by the builder prompt.
- `fem-stress-advisor`: the mesh-size re-run instruction lives in `skill/phase3_build.md` only, no longer in `prompts/part.md`.
- `print-orientation-optimization`: adds a requirement that per-union pipeline commands name union ids, with a single-union part's union id equal to its part id.

## Impact

- Prompt/doc text only: `prompts/part.md`, `skill/phase3_build.md`.
- No `src/` code, schema, JSON contract, or CLI changes. For a part without `unions` every path is unchanged, since its union id is its part id.
