## 1. Memoized load

- [x] 1.1 Audit all `_load_result` callers for in-place mutation of the returned `Workplane` (`write_assembly.py`, `toolpath_speed.py`, `gridfinity_check.py`, `section_select.py`, `quality_gate.py`)
- [x] 1.2 Add the `fresh` kwarg and the `(abspath, sha256, rotate)` memo to `_load_result` in `src/exporters/__init__.py`
- [x] 1.3 Test in `tests/test_exporters.py`: repeat load executes once, edit invalidates, distinct rotate executes per value, `fresh=True` re-executes

## 2. Merged hooked load

- [x] 2.1 Give both hooked checks an optional `load` callable so one can nest inside the other's load
- [x] 2.2 Keep standalone behavior when `load` is omitted
- [x] 2.3 In `quality_gate.py`, run the nested load once for unrotated parts (`_run_hooked_stages`) and feed both stages; rotated parts keep a separate authored-frame feature load
- [x] 2.4 Tests: findings from the merged path equal the standalone results on the existing fixtures in `test_edge_treatment_check.py` and `test_feature_presence_check.py`

## 3. Deliver via shim

- [x] 3.1 Split `export_loaded(result, stem, formats, out_dir)` out of `run_exporters`
- [x] 3.2 Pass `CQ_DELIVER_FORMATS` / `CQ_DELIVER_DIR` to the shim when `--deliver` and no `--print-rotate`; the shim calls `export_loaded`; the wrapper skips the reload in `_handle_deliver` and collects the paths
- [x] 3.3 Test in `tests/test_run_wrapper.py`: deliver output and JSON keys unchanged, script executes once; `--print-rotate` path unchanged

## 4. Gate wiring

- [x] 4.1 Confirm the toolpath-speed and Gridfinity stages hit the cache in a gate run (count executions with a counting script in a test)

## 5. Verify

- [ ] 5.1 Time a gate run on the largest eval case before and after; confirm `--timeout` is not tripped by shim-side delivery
- [x] 5.2 `uv run pytest tests/` and `ruff check` on changed files
- [x] 5.3 Tick TODO.md item 2 and update `reference/scripts.md` for the `--deliver` and `_load_result` notes
