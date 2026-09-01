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
   - A one-line pointer to `REQUIREMENTS.md`, when present, for the full intent/
     topology/fit/constraints spec this design is built from (see Phase 1)
   - The directory layout (mirror the tree in **Model export** in `skill/phase3_build.md`)

If the quality gate failed, summarize the remaining errors and offer to fix the script manually or re-run the gate with `--no-fix` to get a clean report.

Once delivery is reported and `README.md` is written, append one line to
`build/journal.md` (see `skill/resume.md`):

```
- phase4/delivered: README.md written
```
