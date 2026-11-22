---
description: Apply a described change to an existing STEP/BREP solid, keeping its coordinates
argument-hint: <file> <change description>
---

Edit an existing solid: $ARGUMENTS

The first argument is the file, the rest is the change. Stop with one line, writing nothing, if the file does not exist, its extension is not `.step`/`.stp`/`.brep` (CadQuery has no IGES importer), or the change is empty (then ask for it).

`SKILL_DIR` is `${CLAUDE_PLUGIN_ROOT}`. First run `python "${CLAUDE_PLUGIN_ROOT}/src/init_permissions.py" . --check`. If it reports `uninitialized`, do what `/cq-design:init` does (venv in `${CLAUDE_PLUGIN_DATA}/venv`) first. This route is `--route edit` (`pipeline.py status --route edit` lists the steps; it needs no plan or `build/`). Do not run phases 0-2, do not write `BUILD_PLAN.json`, do not run `print_orientation.py` or `quality_gate.py`.

Read `SKILL.md`'s Coordinate system section. Directions in the change ("top", "left", "front") are in the input's own frame: +Z up, +Y north, +X east.

Scripts are created and changed only with `script_ops.py`, never with Edit/Write: write a script's code (or one section's code) to `build/<stem>.op.py`, then run

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/script_ops.py" <new|replace|insert|remove|move> build/<script>.py ...
```

(`new <script> --code <file>`, `replace <script> <section> --code <file>`, `insert <script> --after <section> --code <file>`, `remove <script> <section>`). Every operation is a `# step: <name>` section; a section's code file starts with its marker. A refused command left the file unchanged: read its `errors`, fix the code file, retry.

1. Create `build/edit_input.py`, the input, with `script_ops.py new build/edit_input.py --code build/edit_input.op.py`. Use the input's **absolute** path (scripts run in a temp dir). `import_solid` handles `.step`/`.stp`/`.brep`, checks the solid and repairs an invalid one topologically:

   ```python
   from blocks import import_solid

   # step: import
   result = import_solid(r"<absolute path of the input>")
   ```

   Run step 3's command on it once. A `[cq-design:step-repair]` line in `stdout` means the input failed the grader's validity check and was healed: quote it in the report. A `step_unrepairable` error means the input cannot be healed within the volume limit: stop, deliver nothing, and report the error.

2. Create `build/<stem>_edited.py` with `script_ops.py new --code` (`<stem>` is the input file name without extension, so delivery is named `out/<stem>_edited.step`): the same `# step: import` section (never `cq.importers` directly), then the change as operations on that imported body only, each in its own `# step: <feature>` section -- `cut`/`union` with authored features (`from blocks import ...` where a block fits), or face/edge operations on it (a hole is resized by filling it and re-cutting). Never rebuild the part from scratch, and never translate, rotate or re-centre the import. Measure positions from the imported body (`result.val().BoundingBox()`, `.faces(">Z")`), not from guesses.

3. Run and preview until `success` is true (read each error's `hint`):

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/<stem>_edited.py --preview
   ```

4. Mesh both scripts and diff input (A) against result (B):

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/edit_input.py --deliver --formats stl --output-dir build/edit_diff
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/<stem>_edited.py --deliver --formats stl --output-dir build/edit_diff
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/diff_models.py" build/edit_diff/edit_input.stl build/edit_diff/<stem>_edited.stl --png build/edit_diff/diff.png --region <xmin,ymin,zmin,xmax,ymax,zmax> --expect-volume <lo,hi>
   ```

   `--region` is the bounding box of the feature the change names, measured from the imported input (`BoundingBox()` of its face/edge/feature) and padded by at least 2 mm; include anything the edit moves (a raised face carries its attached features). `--expect-volume` is the net volume change (`only_b_volume - only_a_volume`) your arithmetic on the change's dimensions gives, as a range (blend radius, height delta, diameter delta). State both in the report.

   `identical: true` means the edit did nothing: revise `build/<stem>_edited.py` (a section command on the section at fault). Also revise when `only_a_volume` (removed) / `only_b_volume` (added) or `bbox_delta` contradict the change -- material removed when it only adds, the bounding box moving when the change is internal. Also revise when `localized` is false (changed material outside the region: the edit hit the wrong feature or leaked elsewhere), `volume_in_range` is false, or `region_fraction` is above 0.5 (the region is too broad to prove anything: re-measure it tighter). Look at the input preview (run step 3 on `build/edit_input.py` once), the result preview and `build/edit_diff/diff.png` (common gray, removed red, added green) before accepting.

   When a revision turns a run that had `success: true` into a failing one, or fails a diff check the previous revision passed, undo it before revising again -- never by editing the text back (every run's source is kept):

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/script_history.py" restore @prev build/<stem>_edited.py
   ```

5. After 5 failed iterations of steps 2-4, or when the checks cannot be satisfied, do not deliver an edited body. A wrong edit scores below the unedited input, so deliver the input unchanged (never the repaired body, never overwriting the input):

   ```bash
   mkdir -p out && cp "<absolute path of the input>" "out/<stem>_edited.step"
   ```

   Report that the edit is unverified and the input was delivered unchanged, with the last errors and diff. A `step_unrepairable` input still delivers nothing.

6. Deliver; this writes `out/<stem>_edited.step`. Never write to the input file.

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/src/run_cadquery_model.py" --timeout 600 build/<stem>_edited.py --deliver --formats step --output-dir out
   ```

Report: the delivered path, the repair line if there was one, `only_a_volume`, `only_b_volume`, `bbox_delta`, `localized`, `volume_in_range`, the region and expected volume used, `build/edit_diff/diff.png`, how you read the change's directions, and any assumption you made.
