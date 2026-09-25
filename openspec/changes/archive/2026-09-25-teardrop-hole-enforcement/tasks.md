## 0. Block

- [x] 0.1 Add `peak` param to `teardrop_bore` (`src/blocks/connectors.py`), update `inventory.json` params/use text
- [x] 0.2 Test both peak directions in `tests/test_blocks.py`

## 1. Prompt

- [x] 1.1 Add horizontal-hole rule to `prompts/part.md` (teardrop_bore / teardrop_post / plain vertical); peak faces print-up, use `peak="down"` when print-up is model -Z
- [x] 1.2 Extend `tests/test_render_prompt.py` to assert the rule renders

## 2. Lint

- [x] 2.1 Add side-workplane round-hole advisory to `src/script_lint.py` (suppressed when `teardrop_bore` referenced)
- [x] 2.2 Add tests in `tests/test_script_lint.py`: flagged, suppressed by block use, vertical hole ignored

## 3. Gate hint

- [x] 3.1 Mention `teardrop_bore` in the `overhang_exceeded` warning hint in `src/quality_gate.py`
- [x] 3.2 Add test in `tests/test_quality_gate.py`

## 4. Wrap-up

- [x] 4.1 Tick "teardrop shaped holes not used" in `TODO.md`; run `uv run pytest tests/test_script_lint.py tests/test_render_prompt.py tests/test_quality_gate.py`
