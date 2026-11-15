# FEM and print analysis -- details

Tasks: [TODO.md](../TODO.md#9-fem-and-print-analysis).

### FEM checker follow-ups

`fem_check.py`: solve orthotropic instead of isotropic (currently applies FDM
anisotropy only at the failure criterion, not the stiffness -- confirmed acceptable
for a screening tool, but a real gap if the advisor is ever asked to do more)

`fem_check.py`: source `material_properties.json`'s E/nu/allowable from measured
filament data (own tensile tests, or a vendor data sheet) instead of literature-typical
estimates

`fem_check.py`: model boundary conditions as a real contact/fastener patch instead of
a footprint-radius node selection around a declared interface -- a mis-declared
anchor currently produces a confident wrong number (see `fem-stress-advisor` design.md
risk list)

fem: calculate required wall thickness step 1: global, step 2: regional (open question: how to do? slicer vs model)

fem: more infill only for compression load. infill direction = load direction see: https://filamentfeed.com/article/designing-for-strength-3d-prints-june-2026

### G-code simmulator

Print analysis script (time, weight, slow segments) 

- [ ] Copy `src/print_analysis/` to `cq-design/scripts/` and add a SKILL.md step that runs it after slicing (`python -m print_analysis summary|slow <file.gcode>`)
- [ ] Install `klipper_estimator` (Windows binary) and check the config flag names with `--help` (`--config_file`, `--config_moonraker_url`)
- [ ] Pull limits (accel, velocity) from the U1 Moonraker config and pass them to the estimator
- [ ] Measure the startup offset (PRINT_START, heat-up, homing) on 2-3 real prints and set it as the default `--offset`
- [ ] Compare estimated time and weight with the real print time and spool weight, then adjust density and offset
- [ ] Add G2/G3 arc support in `parser.py` (moves are currently skipped with a warning)
- [ ] Use `klipper_estimator dump-moves` in `slow_segments.py` for the real planned speed (acceleration-limited)
- [ ] Report min-layer-time slowdowns separately from deliberately slow features (bridge, overhang)
- [ ] Set the material per tool (T0-T3) from the U1 spool/RFID data instead of the `--material` flag
- [ ] Test with a real multi-tool U1 G-code (tool changes, prime tower)
- [ ] Optional: expose `mcp_server.py` as an MCP server (`pip install "mcp[cli]"`) and register it in Claude Code
