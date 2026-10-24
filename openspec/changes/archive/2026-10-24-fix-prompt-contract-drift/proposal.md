## Why

Three sub-agent prompts describe tool behaviour that does not exist, and each mismatch burns a bounded retry or audit round:

- `prompts/builder.md:41-43` says geometry-driven `--auto-sections` cuts are "already in the command, 3 cuts total". `render_preview.py` has no such flag, `section_select.py` is imported by nothing, and `render_preview.py:113-114` (`_section_cuts`) makes `--extra-section` *replace* the bounding-box-center cuts. The bore/boss sections the builder believes it has are never rendered, so section-based audit questions fail and consume the single audit round.
- `prompts/audit.md:20` labels the front panel "looking -Y". The renderer draws it from the South looking North (+Y) and labels it "Viewed from South" (`src/preview.py:42`, `:402`). The auditor checks interfaces are "not mirrored" (`audit.md:43`), so the wrong camera direction swaps East/West on exactly that check.
- `prompts/planning.md:145-146` (rule 10) tells the planner to write `load.type: "compression"` with no direction, but `src/build_plan_schema.json:219` requires `dir`. Every base, foot, or cover the planner writes fails validation and spends one of its 3 retries.

## What Changes

- Rewrite the section-cut paragraph in `prompts/builder.md` to state the real behaviour: any `--extra-section` cut replaces the default bounding-box-center cuts, and geometry-driven cuts are only available by running `section_select.py` by hand and passing its `extra_section_args`.
- Correct the `section_select.py` entries in `reference/scripts.md:51` and `FILES.md:65`: drop the claim that `render_preview.py --auto-sections` exists or is forwarded by `run_cadquery_model.py`; describe it as a standalone CLI.
- Replace the panel line in `prompts/audit.md:20` with the renderer's own labels: "Viewed from South (looking North) top-left, Viewed from West (looking East) top-right, Viewed from above (looking down) bottom-left, isometric bottom-right".
- Change planner rule 10 for resting/compressive parts and flat covers to `load: {"dir": [0, 0, -1], "type": "compression"}`, noting the direction is ignored for scoring.
- Wiring up a real `--auto-sections` flag is out of scope (separate change).

## Capabilities

### New Capabilities

### Modified Capabilities
- `preview-cross-sections`: adds a requirement that the builder prompt and script docs describe section-cut selection as implemented (extra sections replace defaults; no `--auto-sections`).
- `visual-self-review`: adds a requirement that the audit prompt names preview panels with the renderer's own camera labels.
- `planning-phase`: adds a requirement that the planner's compression-load instruction yields a schema-valid `load` (with `dir`).

## Impact

- Prompt/doc text only: `prompts/builder.md`, `prompts/audit.md`, `prompts/planning.md`, `reference/scripts.md`, `FILES.md`.
- No `src/` code, schema, JSON contract, or CLI changes. `print_orientation.py:201` already ignores `load_dir` when `load_type == "compression"`, so the fixed `[0, 0, -1]` has no scoring effect.
