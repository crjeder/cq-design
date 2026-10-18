## 1. Builder prompt (`prompts/part.md`)

- [x] 1.1 Remove the "When the plan's `load` declares a solvable case" block (FEM command, status reading, example JSON, mesh re-run note) from the Engineering rationale section
- [x] 1.2 Add one line there: when the orchestrator supplies a FEM `"ok"` result for this part, cite its failure index and location in `check`/`worst_case_stress` instead of a closed-form derivation
- [x] 1.3 Remove the whole "Toolpath-speed advisor" section
- [x] 1.4 Render a builder prompt (`render_prompt.py builder`) for a fixture plan and confirm no `fem_check.py`/`toolpath_speed.py` text remains

## 2. Per-union paths (`skill/phase3_build.md`)

- [x] 2.1 Add one sentence at the top of Print-orientation optimization: a part without `unions` has one union whose id is its part id
- [x] 2.2 Change `print_orientation.py`'s input to `stl/<union_id>.stl` and the speed-candidates command to `--stl stl/<union_id>.stl --emit-candidates <union_id> > build/<union_id>.speed_candidates.json` (and the matching `--speed-model` path)
- [x] 2.3 Change the accepted-result write-up to `build/orientations.json` keyed `{"<union_id>": ...}` and `build/<union_id>.orientation.json` per union
- [x] 2.4 Change the Print finishing `--print-rotate` hint and the Write assembly output description to `<union_id>`
- [x] 2.5 Change the quality gate's `--orientation` to `build/<union_id>.orientation.json`, keeping `--script build/<part_id>.py`
- [x] 2.6 Grep `skill/phase3_build.md` for remaining `<part_id>` in per-union file paths; leave script, prompt, audit, and FEM paths part-keyed

## 3. Verify

- [x] 3.1 Run `uv run pytest tests/test_render_prompt.py` (or the prompt-rendering tests) and `openspec validate fix-phase3-ownership`
