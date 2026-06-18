## 1. Dependency Setup

- [x] 1.1 Verify `cq_warehouse` installs cleanly alongside CadQuery 2.x on Python 3.12
- [x] 1.2 Add `cq_warehouse` to `requirements.txt` (git source, with install comment)

## 2. Documentation

- [x] 2.1 Add "Using cq_warehouse" section to `SKILL.md` covering available fastener classes, instantiation parameters, `simple` flag, and `.add()` / `.cut()` patterns
- [x] 2.2 Include a complete runnable example in `SKILL.md` showing a fastener added to a CadQuery body and exported

## 3. Tests

- [x] 3.1 Add `tests/fixtures/cq_warehouse_fastener.py` — a minimal model script that imports and uses a `HexHeadScrew` and `HexNut`
- [x] 3.2 Add `tests/test_cq_warehouse_integration.py` with:
  - test that the fixture script runs cleanly through `run_cadquery_model.py` (rc=0, success=True, errors=[])
  - test that geometry is reported for the model
  - test that fastener objects carry correct dimensional data
- [x] 3.3 Run the full test suite (`pytest tests/`) and confirm all existing tests pass — 78/78 passing
