## Why

One quality-gate run executes the same part script about six times, each paying `import cadquery` and the full CAD build: the shim, `--deliver`, the edge-treatment hook, the feature-presence hook, toolpath-speed (twice) and Gridfinity. Part scripts are the slowest thing the gate does, so the redundant loads dominate its wall time (TODO.md Optimisation item 2).

## What Changes

- `exporters._load_result` memoizes per process on `(abspath, sha256 of script bytes, print_rotate)`; toolpath-speed (both loads) and Gridfinity collapse onto one load.
- The edge-treatment and feature-presence fillet/chamfer/cut/union hooks run in one shared hooked load instead of two.
- `run_cadquery_model.py --deliver` stops re-importing the script: the shim subprocess, which already holds the loaded `result`, also writes the requested formats when no `--print-rotate` is given.
- No JSON-contract, finding, or exit-code change.

## Capabilities

### New Capabilities

### Modified Capabilities
- `modular-exporters`: adds requirements that a part script is loaded at most once per (script content, print pose) per process, that `--deliver` reuses the shim's load, and that the gate's two hook checks share one load.

## Impact

- `src/exporters/__init__.py`, `src/edge_treatment_check.py`, `src/feature_presence_check.py`, `src/quality_gate.py`, `src/run_model_shim.py`, `src/run_cadquery_model.py`.
- Tests: `test_exporters.py`, `test_edge_treatment_check.py`, `test_feature_presence_check.py`, `test_run_wrapper.py`.
