## 1. render_prompt.py

- [x] 1.1 Change `validate_args(plan, part)` to `validate_args(plan, part, is_final)`, appending `--expected-dims`/`--dim-tolerance` only when `is_final` is true.
- [x] 1.2 In `render_builder`, compute `part_stages` first, then build one validate command per stage (`is_final = stage is part_stages[-1]`) and join into `{{VALIDATE_ARGS}}`.

## 2. prompts/builder.md

- [x] 2.1 Replace the single `{{VALIDATE_ARGS}}` command block in Commands with the per-stage command text produced by `render_builder`.
- [x] 2.2 Remove the `dimension_mismatch` exception clause from step 3 ("Exception: when every error is `dimension_mismatch` and this is a `base_shape`/`features` stage still missing later geometry, carry on.").

## 3. Tests

- [x] 3.1 Update/add `tests/test_render_prompt.py` cases: staged part omits `--expected-dims` on non-final stages and includes it on the final stage; non-staged (`full`) part includes it.
- [x] 3.2 Run `uv run pytest tests/test_render_prompt.py` and confirm green.
