## 1. Severity-weighted support cost (mesh_io)

- [x] 1.1 Add `support_cost(mesh, overhang_deg, exponent)` to `src/mesh_io.py` returning a
      severity-weighted scalar (per downward face: `area * |lean_past_limit| ** exponent`),
      leaving `overhang_metrics` and its `overhang_area_mm2` unchanged
- [x] 1.2 Add unit tests in `tests/test_mesh_io.py`: a near-horizontal overhang costs more
      than a just-past-limit overhang of equal area; faces at/under the limit cost zero

## 2. Orientation support score + bed-contact band (print_orientation)

- [x] 2.1 Add a derived `SUPPORT_EXPONENT` module constant (chosen by us, not Tweaker-3's
      value) and a `FIRST_LAYER_BAND_MM` constant
- [x] 2.2 Update `_support_metrics` to use `support_cost` for the support ranking key and
      to count bed contact within `FIRST_LAYER_BAND_MM` of the lowest point
- [x] 2.3 Update the on-bed test in `_gentle_incline_fraction` to use the same band
- [x] 2.4 Update `tests/test_print_orientation.py`: steeper overhang yields worse support
      score at equal area (covered by mesh_io severity tests); near-coplanar resting face
      counts as bed contact
      
## 3. Area-cumulation candidate source

- [x] 3.1 Add an area-cumulation helper that accumulates face-area-weighted normals and
      returns the top-N directions, and merge its output into `enumerate_candidate_normals`
      before the `NORMAL_MERGE_DEG` dedup pass (hull + axis candidates retained)
- [x] 3.2 Test that a mesh with a dominant large flat region surfaces the orientation
      laying that region on the bed, and that the candidate set stays bounded after dedup

## 4. `min_build_height` objective

- [x] 4.1 Add `min_build_height` to `OPTIMIZE_MODES` and compute each candidate's posed
      bounding-box Z extent
- [x] 4.2 Extend `_select` with the `min_build_height` branch: minimize Z extent within a
      tolerance band, tiebreak by strength, support, then `idx`
- [x] 4.3 Surface the build-height in the result/rationale without changing the existing
      score fields
- [x] 4.4 Test that `min_build_height` selects the lowest-profile candidate and is
      deterministic across repeated runs

## 5. Finish

- [x] 5.1 Run `ruff check --fix` and `ruff format` on changed files
- [x] 5.2 Run `uv run pytest tests/test_print_orientation.py tests/test_mesh_io.py`
- [x] 5.3 `openspec validate tweaker3-print-orientation --strict`
