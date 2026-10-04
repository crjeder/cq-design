## 1. model_export

- [x] 1.1 Add `formats` parameter to `export_model`; validate keys against the exporter registry minus `stl`/`3mf` before writing
- [x] 1.2 Write `<union-id>.<ext>` per union from `placed[uid]` via the registry exporter; add `format_files` to the result dict
- [x] 1.3 Add `--formats` to `model_export.main` and pass it through

## 2. build.py

- [x] 2.1 Add `--formats` to `build_template.py`, exit non-zero on an unsupported key, list the written files in the report

## 3. Tests and docs

- [x] 3.1 `tests/test_model_export.py`: STEP written per union, same bbox and volume as the union STL, default output unchanged, unsupported key raises with no files written
- [x] 3.2 `tests/test_build_script.py`: `--formats step` and unsupported-key cases
- [x] 3.3 Update README command-line reference and STEP section, `reference/scripts.md`, and `CLAUDE.md` if it lists build.py outputs
