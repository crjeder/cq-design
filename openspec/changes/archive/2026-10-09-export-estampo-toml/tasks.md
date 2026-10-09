## 1. Verify and schema

- [x] 1.1 Read estampo docs/config.md; confirm override key names (layer height, infill, walls, support, brim) and `[[parts]]` keys, and record the version in the generated header
- [x] 1.2 Add optional `slicer.estampo` (`engine`, `printer`, `process`, `filaments`) to `src/printer_profile_schema.json`; extend `tests/test_printer_profile_validate.py`

## 2. Writer

- [x] 2.1 Create `src/estampo_export.py` with `write_estampo_toml` (parts from the STL file list with rotate [0,0,0], allowlisted overrides, commented placeholders)
- [x] 2.2 Add `estampo` to `FORMATS` in `src/deliverables.py`, force `stl`, call the writer, report the file
- [x] 2.3 Update the `--formats` help text and docstring in `src/build_template.py`

## 3. Tests and docs

- [x] 3.1 Add `tests/test_estampo_export.py` (fast, no CadQuery): single union, print-in-place plate, absent values omitted, placeholders
- [x] 3.2 Add the `build.py --formats estampo` scenario to the existing build tests
- [x] 3.3 Update `reference/scripts.md`, the CLAUDE.md file layout, the estampo row in `documentation/related_projects.md` and the TODO.md slicer-parameters item
