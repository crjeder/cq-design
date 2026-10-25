## 1. Renderer

- [x] 1.1 Add `--auto-sections` to `src/render_preview.py`; extend `_section_cuts` to fill up to 3 cuts with `select_sections(..., reserved=extra)` on the compound of all result solids, falling back to bbox centers; warn-only on selector errors; flag implies `--cross-sections`

## 2. Wrapper and builder command

- [x] 2.1 Add `--auto-sections` to `src/run_cadquery_model.py` and forward it in `_render_preview`
- [x] 2.2 Add `--auto-sections` to `render_prompt.validate_args`

## 3. Tests

- [x] 3.1 `tests/test_auto_sections.py`: slot fill with reserved cuts, bbox fallback, selector error warns, CLI writes the auto section file, wrapper forwards the flag

## 4. Docs

- [x] 4.1 `prompts/builder.md` section-cut paragraph describes the real order: extra-section, then auto (3 total), then bbox centers
- [x] 4.2 `reference/scripts.md` `section_select.py` row and `render_preview`/`run_cadquery_model` mentions; `FILES.md:65`

## 5. Verify

- [x] 5.1 `uv run pytest tests/test_auto_sections.py tests/test_section_select.py tests/test_preview.py tests/test_render_prompt.py tests/test_run_wrapper.py`
- [x] 5.2 `openspec validate wire-auto-sections`
