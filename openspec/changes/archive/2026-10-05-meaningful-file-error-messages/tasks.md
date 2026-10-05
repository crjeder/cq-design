## 1. Shared helper

- [x] 1.1 Add `InputFileError` and `read_json(path, role)` to `src/units.py`; make `load_plan` use it
- [x] 1.2 Add fast tests in a new `tests/test_input_errors.py` for missing, directory, and malformed-JSON paths (no CadQuery)

## 2. CLI entry points

- [x] 2.1 Make `InputFileError` a `SystemExit` so every `load_plan` CLI exits 1 with `error: <msg>` and no traceback; route `model_export.py` orientations read through `read_json`
- [x] 2.2 Route `plan.py summary` through `load_plan` (`validate`/profile already return guarded messages)
- [x] 2.3 Add a test per CLI family asserting exit 1, one-line stderr, no `Traceback`

## 3. JSON-contract scripts

- [x] 3.1 `quality_gate.py`: read plan/orientation/config via the helper; emit `file_error` in `errors` on failure
- [x] 3.2 `run_cadquery_model.py`: wrap the print-orientation read; emit `file_error`
- [x] 3.3 Tests asserting the contract keys are all present alongside a `file_error` entry

## 4. STL loaders

- [x] 4.1 `mesh_io.py` and `measure_stl.py`: separate "not found" from "not a valid STL" messages
- [x] 4.2 Tests for both cases

## 5. Docs

- [x] 5.1 Document `file_error` in `reference/scripts.md`
- [x] 5.2 Run the affected tests
