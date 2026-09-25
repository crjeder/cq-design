## Why

Orientation-dependent print treatments (teardrop peak direction, chamfer-vs-fillet per edge-to-bed angle, first-layer chamfer) are baked into the part script at authoring time, before `print_orientation.py` has chosen a pose. The builder guesses the pose; a wrong guess is only caught by the quality gate and fixed by a full LLM `fix:` round. The pose is known deterministically after orientation, so these treatments should resolve then, without an LLM.

## What Changes

- New `print_frame` helper (importable from `blocks`): `print_up()` returns the print-up direction in the part's authored frame. It reads `CQ_PRINT_ROTATE` (the accepted orientation's `rotate` list, JSON) from the environment and defaults to +Z when unset, so existing scripts and the authoring pass behave exactly as today.
- `teardrop_bore` / `teardrop_post` accept `print_up=` (a vector) as an alternative to `peak=`, orienting the peak toward it.
- Builder prompt: orientation-dependent features go through `print_up()`-aware helpers; the script carries no hard-coded pose guess.
- New finishing pass in Phase 3, after orientation and before model export: re-run each part script with `CQ_PRINT_ROTATE` set from `build/orientations.json`, then re-score orientation on the result and warn if the chosen pose changed.
- `run_cadquery_model.py` gains `--print-rotate <orientation.json>` to set the env for a run; `edge_treatment_check.py` and `build_template.py` pass the same value when they re-run scripts.
- Provenance: the export manifest stamps the `rotate` used, so a stale finishing pass is detectable.

## Capabilities

### New Capabilities
- `print-pose-finishing`: pose-aware re-run of part scripts after orientation, the `print_up()` contract, and the pose-stability guard.

### Modified Capabilities

## Impact

`src/blocks/` (new `print_frame.py`, `connectors.py`, `__init__.py`, `inventory.json`), `src/run_cadquery_model.py`, `src/edge_treatment_check.py`, `src/build_template.py`, `src/model_export.py`, `src/freshness.py`, `prompts/part.md`, `skill/phase3_build.md`, tests. JSON output contract unchanged (new optional field only). Builds on `teardrop-hole-enforcement` (`peak` param).
