## Why

`src/section_select.py` picks section planes through bore/boss axes, but nothing imports it: `render_preview.py` has no `--auto-sections` flag and `_section_cuts` makes any `--extra-section` cut replace the bounding-box-center cuts. Bores and bosses away from the plan's declared positions are never sectioned, so the builder and auditor cannot check them. `fix-prompt-contract-drift` corrects the docs to say so; this change makes the flag real and then documents it.

## What Changes

- `render_preview.py --auto-sections`: after the `--extra-section` cuts, call `select_sections(shape, max_cuts=3, reserved=<extra-section cuts>)` and append its cuts until there are 3 in total. The flag implies `--cross-sections`.
- Bounding-box-center cuts stay the fallback when there are no extra-section cuts and the selector returns none.
- A selector exception only prints a `WARNING` to stderr; the render continues with whatever cuts it already has, or falls back to the bbox-center cuts.
- `run_cadquery_model.py --auto-sections` forwards the flag to `render_preview.py` with `--preview`.
- `render_prompt.validate_args` adds `--auto-sections` to the builder's validate command.
- Docs: `prompts/builder.md` section-cut paragraph, the `section_select.py` row in `reference/scripts.md`, and `FILES.md:65` describe the flag.

## Capabilities

### New Capabilities

### Modified Capabilities
- `preview-cross-sections`: adds a requirement for geometry-driven `--auto-sections` cuts that fill up to 3 cuts after `--extra-section`, with bbox-center fallback and warn-only selector errors.

## Impact

- Code: `src/render_preview.py`, `src/run_cadquery_model.py`, `src/render_prompt.py`.
- Tests: new `tests/test_auto_sections.py`.
- Docs: `prompts/builder.md`, `reference/scripts.md`, `FILES.md`.
- New CLI flag only; no JSON contract keys change. Without the flag, behaviour is the same as today.
- Ordering: lands after `fix-prompt-contract-drift`, and overwrites the same doc paragraphs that change rewrites.
