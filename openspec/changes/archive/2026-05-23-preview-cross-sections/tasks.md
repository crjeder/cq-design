## 1. preview.py - Cross-section helpers and render_multi_view update

- [x] 1.1 Add `_cut_half(shape, axis, center)` helper that creates an axis-aligned half-space box and returns `shape.cut(half_box)`, catching OCC exceptions and returning `None` on failure
- [x] 1.2 Add `cross_sections=False` parameter to `render_multi_view`; when `True`, compute shape centroid, call `_cut_half` for each axis, and append the three cut views to the `images` list
- [x] 1.3 Update tile layout in `render_multi_view`: when `cross_sections=True` set `rows=3` and use the three cross-section views (Section Y, Section X, Section Z) for row 3 with graceful blank-tile fallback when a cut returns `None`

## 2. render_preview.py - --cross-sections CLI flag

- [x] 2.1 Add `--cross-sections` boolean flag to `argparse` in `render_preview.py`
- [x] 2.2 Pass `cross_sections=args.cross_sections` to `preview.render_multi_view`; verify the flag is silently ignored when `--views iso` is used

## 3. run_cadquery_model.py - Forward --cross-sections

- [x] 3.1 Add `--cross-sections` flag to the `argparse` parser in `run_cadquery_model.py`
- [x] 3.2 In `_render_preview`, extend the subprocess argv to include `--cross-sections` when `args.cross_sections` is truthy (only when `--preview` is also set)

## 4. Tests

- [x] 4.1 Add test in `tests/test_preview.py` (or `test_run_wrapper.py`) that calls `render_multi_view(box_wp, tmp_path, cross_sections=True)` and asserts the output PNG height is taller than the default six-view tile
- [x] 4.2 Add test verifying graceful fallback: mock `_cut_half` to raise an OCC exception and assert render completes without error and produces a nine-tile image (with blank fallback for the failing view)
- [x] 4.3 Add CLI test in `test_run_wrapper.py` for `run_cadquery_model.py --preview --cross-sections` asserting `previews` is non-empty in JSON output

## 5. Spec compliance check

- [x] 5.1 Run `uv run pytest tests/test_preview.py tests/test_run_wrapper.py` and confirm all new and existing tests pass
- [x] 5.2 Run `uv run ruff check src/preview.py src/render_preview.py src/run_cadquery_model.py` and fix any lint issues
