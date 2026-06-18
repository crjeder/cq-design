## Why

CadQuery scripts must hand-code every hardware component from scratch. `cq_warehouse` provides a parametric ISO hardware catalog (fasteners, threads, inserts) that works natively with CadQuery 2.x — each part is a CadQuery `Solid` that slots directly into any model. This eliminates guesswork on bolt head heights, nut flats, and thread geometry for the most common hardware.

## What Changes

- Add `cq_warehouse` to `requirements.txt` (installed from GitHub; not yet on PyPI)
- Add a "Using cq_warehouse" section to `SKILL.md` covering imports, instantiation, `simple` flag, and clearance/tap hole helpers
- Add an integration test verifying a `cq_warehouse`-based script runs cleanly through `run_cadquery_model.py`

No changes to `run_cadquery_model.py` or the orchestration pipeline — `cq_warehouse` parts are plain CadQuery Solids that require no special wrapper support.

## Capabilities

### New Capabilities
- `cq-warehouse-catalog`: Standard hardware (ISO fasteners, heat-set inserts) available in model scripts via `from cq_warehouse.fastener import ...`

### Modified Capabilities

## Impact

- `requirements.txt`: new dependency `cq_warehouse` (git source)
- `SKILL.md`: documentation addition only
- No breaking changes to any existing scripts or pipeline
