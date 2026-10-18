## 1. Helpers

- [x] 1.1 Add `_size_limit(body, selector)` in `src/cq_verify.py`: for each non-selected edge sharing a vertex (`isSame`) with a selected edge, limit = length, halved when its other vertex also touches a selected edge; return (min limit, limiting edge length)
- [x] 1.2 Add `check_fillet(body, radius, selector=None, label="")` raising `_fail("fillet_radius", ...)` when `radius >= limit`; return `body`
- [x] 1.3 Add `check_chamfer(body, length, selector=None, label="")` with kind `chamfer_size`
- [x] 1.4 Add `check_ligament(wall_mm, hole_d_mm, min_mm, label="")` with kind `thin_ligament`; return the ligament
- [x] 1.5 Extend the module docstring list with the three helpers

## 2. Wrapper

- [x] 2.1 Add `fillet_radius`, `chamfer_size`, `thin_ligament` hints to `_VERIFY_HINTS` in `src/run_cadquery_model.py` (each says which number to reduce, or to back off 0.1 mm from the limit)

## 3. Guidance

- [x] 3.1 Update the import example and add bullets for the three helpers plus the one-line adjacent-edge rule in `prompts/part.md` "Construction-time verification"; add the new kinds to the typed-error list sentence at the end of that section

## 4. Tests

- [x] 4.1 `tests/test_cq_verify.py`: fillet too large raises with kind and label; valid radius returns the same object; `|Z` R3 on a 20x20x5 box passes; chamfer too large / valid; ligament thin / sufficient
- [x] 4.2 `tests/test_run_wrapper.py`: add the three kinds to `test_translate_stderr_classifies_verify_markers`; add an end-to-end fixture script with an over-large fillet yielding `errors[0].type == "fillet_radius"` and a non-empty hint
- [x] 4.3 Run `uv run pytest tests/test_cq_verify.py tests/test_run_wrapper.py` and `ruff check --fix` / `ruff format` on changed files
