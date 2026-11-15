## 1. Implementation

- [x] 1.1 `estampo_export.py`: add `wall_min_mm` param to `estampo_toml` / `write_estampo_toml`; emit `wall_loops = ceil(round(wall_min_mm / line_width_mm, 6))` when both present
- [x] 1.2 `deliverables.py`: pass `constraints.get("wall_min_mm")` to `write_estampo_toml`

## 2. Tests and docs

- [x] 2.1 `tests/test_estampo_export.py`: 1.2/0.45 -> 3, 0.9/0.45 -> 2, missing line width or wall -> no key
- [x] 2.2 Update `reference/scripts.md` deliverables row; tick the TODO.md slicer-parameters item
- [x] 2.3 Run `uv run pytest tests/test_estampo_export.py tests/test_build_script.py`
