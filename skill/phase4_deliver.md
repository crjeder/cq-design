# Phase 4: Deliver

Report to the user:

1. **Status** - which parts passed, which had remaining warnings or errors. If
   `build/quality_gate.json` carries a `telemetry_missing` warning (`source: "telemetry"`),
   name the missing `build/attempts.jsonl` and note that this session produced no
   measurement data. If it carries a `parameters_missing` warning (`source: "parameters"`),
   name the missing `parameters.py` and note that Phase 1's dimension checkpoint recorded
   sourcing but the provenance file was never written
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
   - The directory layout:
     ```
     README.md, REGENERATE.md, parameters.py, model.3mf, BUILD_PLAN.json, printer_profile.json
     pyproject.toml, .python-version, uv.lock
     build/   <part_id>.py (editable part scripts), build.py, orientations.json, *.orientation.json
     lib/     bundled build tooling
     stl/     <part_id>.stl (assembled pose), plate_<n>.stl (print pose)
     preview/ <part_id>_preview.png, _section_*.png, _detail_*.png
     ```
   - A one-line pointer to `REGENERATE.md` (see step 6)
6. **Write `REGENERATE.md`** at the project root -- the prompt that lets the user rebuild
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
   `REGENERATE.md` (an unreconciled correction is already caught by `plan_validate.py`).

If the quality gate failed, summarize the remaining errors and offer to fix the script manually.

Once delivery is reported and `README.md` / `REGENERATE.md` are written, append one line to
`build/journal.md` (see `skill/resume.md`):

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/journal.py" append build/journal.md \
    phase4/delivered "README.md + REGENERATE.md written"
```
