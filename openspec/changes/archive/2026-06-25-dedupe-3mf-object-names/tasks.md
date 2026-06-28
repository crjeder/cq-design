## 1. Name-deduplication pass

- [x] 1.1 In `src/model_export.py`, compute each part's base name with `_object_name(part.get("description", ""), part["id"])`, count occurrences (e.g. `collections.Counter`), and build the final name list: suffix `f"{base} ({pid})"` only when the base name occurs more than once, else keep the base name.
- [x] 1.2 Use the deduped name list when building the `objects` tuples for `write_named_3mf` (replace the inline `_object_name(...)` call at `model_export.py:96`). Keep `_object_name` itself unchanged.

## 2. Tests

- [x] 2.1 `tests/test_model_export.py`: two parts with identical non-empty descriptions -> the two 3MF object names are distinct and each ends with its part id; assert no duplicate names across the 3MF.
- [x] 2.2 Distinct descriptions -> object names equal the plain sanitized descriptions (no id suffix), guarding against churn in the common case.
- [x] 2.3 (If not already covered) empty descriptions still fall back to the unique part id and remain distinct.

## 3. Verification

- [x] 3.1 `uv run pytest tests/test_model_export.py tests/test_stl_to_3mf.py` pass.
- [x] 3.2 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on `src/model_export.py`.
- [x] 3.3 Update the `model_export.py` row/wording in `CLAUDE.md` if needed (note unique object names); remove the resolved "3MF object names not deduped" line from `TODO.md`.
