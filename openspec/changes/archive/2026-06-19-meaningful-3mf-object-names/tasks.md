## 1. Name derivation

- [x] 1.1 Add `_object_name(description: str, fallback: str) -> str` helper to `src/model_export.py`: collapse internal whitespace/newlines to single spaces, strip control characters, trim, cap length (64 chars), and return `fallback` (the part id) when the result is empty
- [x] 1.2 In `export_model`, build the `objects` tuples using `_object_name(part["description"], part["id"])` as the object name instead of `part["id"]`

## 2. Tests

- [x] 2.1 In `tests/test_model_export.py`, parse the exported `model.3mf` and assert each `<object>` `name` equals the sanitized part description (not the id)
- [x] 2.2 Add a case with a description containing newlines/control chars and a length over the cap; assert the written name is single-line, control-char-free, and length-bounded, and the 3MF still loads
- [x] 2.3 Add a case where the sanitized description is empty; assert the name falls back to the part id

## 3. Verify

- [x] 3.1 Run `uv run pytest tests/test_model_export.py`
- [x] 3.2 Run `ruff check --fix src/model_export.py tests/test_model_export.py` and `ruff format` on the changed files
