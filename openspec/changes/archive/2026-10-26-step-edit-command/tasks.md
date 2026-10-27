## 1. Edit command

- [x] 1.1 Write `commands/edit.md` (frontmatter `description`, `argument-hint: <file> <change description>`): argument checks (exists, STEP/BREP extension, non-empty description), init check as in `commands/design.md`
- [x] 1.2 In `commands/edit.md`: author `build/edit_input.py` (plain import) and `build/<stem>_edited.py` (import + change as ops on the imported body only, no translate/rotate, directions read in the input frame)
- [x] 1.3 In `commands/edit.md`: validate loop (`run_cadquery_model.py build/<stem>_edited.py --preview` until `success`), mesh both with `--deliver --formats stl --output-dir build/edit_diff`, `diff_models.py ... --png`, iterate on `identical: true` or a diff contradicting the description, cap at 5 iterations
- [x] 1.4 In `commands/edit.md`: deliver with `--deliver --formats step --output-dir out`, writing `out/<stem>_edited.step` (script named after the input, no rename: benchmark Bash allows only uv/python), never touch the input; report path, diff volumes, `bbox_delta`, diff PNG, direction reading
- [x] 1.5 Confirm `tests/test_prose_layer.py` passes (paths and CLI flags in `commands/edit.md` exist)

## 2. Frame and diff checks

- [x] 2.1 Test: import + re-export of a STEP through `build/edit_input.py`-style script and `diff_models.py` on both meshes reports `identical: true` (no-op edit is detected)
- [x] 2.2 Test: a script cutting a hole from the imported body diffs with `only_a_volume > 0`, `only_b_volume == 0`, and its exported STEP has the input's bounding box (frame preserved)

## 3. CADGenBench harness

- [x] 3.1 Move the `build/build.py --formats step` sentence out of `FIDELITY` into the generation branch of `build_prompt`
- [x] 3.2 Edit branch of `build_prompt` returns `/cq-design:edit input.step <description>` with `UNATTENDED` and `FIDELITY`
- [x] 3.3 Tests in `tests/test_cadgenbench_run.py` for both `build_prompt` branches (edit prompt contains the command and description and not `build/build.py`; generation prompt unchanged apart from the moved sentence)
- [ ] 3.4 Run one edit fixture (`--fixtures <id>`) to confirm headless `claude -p` expands the plugin command and `out/input_edited.step` is picked up; if not, switch the prompt to the fallback wording in design.md

## 4. Docs

- [x] 4.1 Add `edit` to the `SKILL.md` command list line, the `README.md` commands paragraph, and the `FILES.md` `commands/` line and add `commands/edit.md`
- [x] 4.2 Update `evals/README.md`'s `cadgenbench_run.py` entry for the edit prompt
- [x] 4.3 Tick the TODO.md "edit mode (import step) and apply changes" item
