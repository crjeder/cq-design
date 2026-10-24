# Phase 4: Deliver

First generate the model files (the project was bundled and synced at the end of Phase 3):

```bash
uv run python build/build.py
```

This writes the profile's `slicer.preferred_format` into `out/`. If `build.py` fails, show its
`build failed:` message and stop. A different format later is `uv run python build/build.py
--formats <list>` or `/cq-design:build <format>`.

Report to the user:

1. **Status** - which parts passed, which had remaining warnings or errors. If
   any `build/<union_id>.quality_gate.json` (one per union, written in Phase 3) carries a `telemetry_missing` warning (`source: "telemetry"`),
   name the missing `build/attempts.jsonl` and note that this session produced no
   measurement data. If it carries a `parameters_missing` warning (`source: "parameters"`),
   name the missing `parameters.py` and note that Phase 1's dimension checkpoint recorded
   sourcing but the provenance file was never written. If `print_recipe.orientation` carries
   `estimated_print_time_s`, report it alongside `speed_efficiency` and note plainly that
   it is a slicer-free lower bound (no travel between islands, solid top/bottom layers,
   seam/retraction time, or heat-up) -- useful for comparing poses, not for quoting against
   a real slicer's estimate. If `stalled` is true, the pose is minimum-layer-time bound
   (print time is driven by height and the profile's floor, not geometry); offer the
   stated remedies (flatter pose, thicker stalling feature, more copies on the plate) and
   **ask before changing plate layout or part count** -- more copies is never applied
   without the user's explicit approval (see `reference/scripts.md`, `src/toolpath_speed.py`)
2. **Preview images** - display any `.png` files from `preview/`
3. **Print recipe** - show each union's `print_recipe` from its `build/<union_id>.quality_gate.json`
4. **Output files** - list the files `build.py` wrote to `out/`, and note
   that the working directory is a self-contained uv project (committed `uv.lock`): the
   user regenerates them, or any other format, with `uv run python build/build.py
   [--formats 3mf,stl,step,...]` or `/cq-design:build [format]`, no skill re-invoke. Also list `standalone/` (see step 8): the part scripts alone, with only
   the helper modules they import and a cadquery-only `pyproject.toml`.
   When any union declares `filament`, list each union's slot (`body` -> 1, `ring` -> 2)
   and tell the user `model.3mf` preassigns those slots: they load the matching colors
   into those slots in the slicer, which flags a slot the printer does not have
5. **Hardware to buy** - when `BUILD_PLAN.json`'s `bom` is non-empty, list every row
   (item, spec, qty, parts, note) so the user knows what to source before assembly
6. **Write `README.md`** at the project root (create it fresh each delivery; it's a
   generated summary, not something the user hand-edits). Include:
   - What the project is and its intent (from `BUILD_PLAN.json`'s `intent` field)
   - The parts list (id, description, dimensions) and printer/material/nozzle
   - Build instructions: `uv sync` then `uv run python build/build.py`, noting `build/`
     holds the editable part scripts and everything else regenerates from them
   - A one-line pointer to `parameters.py` for the sourced real-world measurements this
     design is based on (see Phase 2)
   - A **Hardware to buy** section listing every `bom` row (item, spec, qty, parts, note),
     omitted when `bom` is absent or empty
   - The directory layout:
     ```
     README.md, REGENERATE.md, parameters.py, BUILD_PLAN.json, profile.json
     pyproject.toml, .python-version, uv.lock
     build/   <part_id>.py (editable part scripts), build.py, orientations.json, *.orientation.json
     lib/     bundled build tooling
     standalone/ <part_id>.py + only the helpers they import, pyproject.toml (cadquery only)
     stl/     <part_id>.stl (assembled pose, input to the checks), export_manifest.json
     out/     the requested model files, all in print pose: model.3mf, or <part_id>.stl + plate_<n>.stl, or step/obj/iges/scad per union
     preview/ <part_id>_preview.png, _section_*.png, _detail_*.png
     ```
   - A one-line pointer to `REGENERATE.md` (see step 7)
7. **Write `REGENERATE.md`** at the project root -- the prompt that lets the user rebuild
   this design from scratch in a fresh session (a better model, a newer skill, a different
   skill), carrying the approved `intent`, the verbatim `request_log`, `parameters.py`, the
   `sketches/` list and the print target. Generated, not hand-authored -- do not write this
   file yourself, and regenerate it (overwrite) on every delivery so it reflects the latest
   corrections:

   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/regen_prompt.py" --plan BUILD_PLAN.json --out REGENERATE.md
   ```

   Read the result before reporting: if the `What to build` section is a bare noun phrase
   rather than the approved reformulation, fix `intent` and re-run rather than editing
   `REGENERATE.md` (an unreconciled correction is already caught by `plan.py validate`).

8. **Write `standalone/`** -- the minimal deliverable for users who only want the parametric
   part code, not `lib/`. Overwritten on every delivery:

   ```bash
   uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/export_standalone.py" --parts-dir build --out standalone --parameters parameters.py
   ```

If the quality gate failed, summarize the remaining errors and offer to fix the script manually.

Once delivery is reported and `README.md` / `REGENERATE.md` are written, append one line to
`build/journal.md` (see `skill/resume.md`):

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" journal append build/journal.md \
    phase4/delivered "README.md + REGENERATE.md written"
```
