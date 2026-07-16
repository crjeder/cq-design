# Phase 4: Deliver

Report to the user:

1. **Status** - which parts passed, which had remaining warnings or errors
2. **Preview images** - display any `.png` files from `preview/`
3. **Print recipe** - show `print_recipe` from `build/quality_gate.json`
4. **Output files** - list `model.3mf` (project root) and the STLs in `stl/`, and note
   that the working directory is a self-contained uv project (committed `uv.lock`): the
   user regenerates the plates in print orientation with `uv run python build/build.py`,
   no skill re-invoke
5. **Write `README.md`** at the project root (create it fresh each delivery; it's a
   generated summary, not something the user hand-edits). Include:
   - What the project is and its intent (from `BUILD_PLAN.json`'s `intent` field)
   - The parts list (id, description, dimensions) and printer/material/nozzle
   - Build instructions: `uv sync` then `uv run python build/build.py`, noting `build/`
     holds the editable part scripts and everything else regenerates from them
   - A one-line pointer to `parameters.py` for the sourced real-world measurements this
     design is based on (see Phase 2)
   - The directory layout (mirror the tree in **Model export** in `skill/phase3_build.md`)

If the quality gate failed, summarize the remaining errors and offer to fix the script manually or re-run the gate with `--no-fix` to get a clean report.
