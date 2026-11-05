---
description: Apply a described change to an existing STEP/BREP solid, keeping its coordinates
argument-hint: <file> <change description>
---

Edit an existing solid: $ARGUMENTS

The first argument is the file, the rest is the change. Stop with one line, writing nothing, if the file does not exist, its extension is not `.step`/`.stp`/`.brep` (CadQuery has no IGES importer), or the change is empty (then ask for it).

`SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}`. First run `python "${CLAUDE_PLUGIN_ROOT}/src/init_permissions.py" . --check`. If it reports `uninitialized`, do what `/cq-design:init` does (venv in `${CLAUDE_PLUGIN_DATA}/venv`) first. Do not run phases 0-2, do not write `BUILD_PLAN.json`, do not run `print_orientation.py` or `quality_gate.py`.

Read `SKILL.md`'s Coordinate system section. Directions in the change ("top", "left", "front") are in the input's own frame: +Z up, +Y north, +X east.

1. Write `build/edit_input.py`, the input. Use the input's **absolute** path (scripts run in a temp dir). `import_solid` handles `.step`/`.stp`/`.brep`, checks the solid and repairs an invalid one topologically:

   ```python
   from blocks import import_solid

   result = import_solid(r"<absolute path of the input>")
   ```

   Run step 3's command on it once. A `[cq-design:step-repair]` line in `stdout` means the input was invalid and was repaired: quote it in the report. A `step_unrepairable` error means the input cannot be repaired within the volume limit: stop, deliver nothing, and report the error.

2. Write `build/<stem>_edited.py` (`<stem>` is the input file name without extension, so delivery is named `out/<stem>_edited.step`): the same `import_solid` import (never `cq.importers` directly), then the change as operations on that imported body only -- `cut`/`union` with authored features (`from blocks import ...` where a block fits), or face/edge operations on it (a hole is resized by filling it and re-cutting). Never rebuild the part from scratch, and never translate, rotate or re-centre the import. Measure positions from the imported body (`result.val().BoundingBox()`, `.faces(">Z")`), not from guesses.

3. Run and preview until `success` is true (read each error's `hint`):

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/<stem>_edited.py --preview
   ```

4. Mesh both scripts and diff input (A) against result (B):

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/edit_input.py --deliver --formats stl --output-dir build/edit_diff
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/<stem>_edited.py --deliver --formats stl --output-dir build/edit_diff
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/diff_models.py" build/edit_diff/edit_input.stl build/edit_diff/<stem>_edited.stl --png build/edit_diff/diff.png
   ```

   `identical: true` means the edit did nothing: revise `build/<stem>_edited.py`. Also revise when `only_a_volume` (removed) / `only_b_volume` (added) or `bbox_delta` contradict the change -- material removed when it only adds, the bounding box moving when the change is internal. Look at the input preview (run step 3 on `build/edit_input.py` once), the result preview and `build/edit_diff/diff.png` (common gray, removed red, added green) before accepting.

   When a revision turns a run that had `success: true` into a failing one, or fails a diff check the previous revision passed, undo it before revising again -- never by editing the text back (every run's source is kept):

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/script_history.py" restore @prev build/<stem>_edited.py
   ```

5. After 5 failed iterations of steps 2-4, stop: deliver nothing and report the last errors and diff.

6. Deliver; this writes `out/<stem>_edited.step`. Never write to the input file.

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/<stem>_edited.py --deliver --formats step --output-dir out
   ```

Report: the delivered path, the repair line if there was one, `only_a_volume`, `only_b_volume`, `bbox_delta`, `build/edit_diff/diff.png`, how you read the change's directions, and any assumption you made.
