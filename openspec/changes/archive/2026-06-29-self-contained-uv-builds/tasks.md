## 1. Project-scaffold template assets

- [x] 1.1 Add a `pyproject.toml` template asset (in the skill's `src/`) for the delivered working directory: runtime deps only (cadquery, trimesh, numpy, lxml, matplotlib, pillow, scipy, networkx), `requires-python = ">=3.10,<3.13"`, `package = false`, and the `cq-warehouse` git source under `[tool.uv.sources]`. No dev group.
- [x] 1.2 Add a `.python-version` template asset selecting a 3.10-3.12 interpreter (match the repo's pinned 3.12).
- [x] 1.3 Determine the exact import closure of `build.py` from `src/` (`exporters` incl. `threemf_multi`, `blocks` incl. `inventory.json`/`inventory_schema.json`, `mesh_io`, `model_export`, `print_orientation`, `placement`, and their intra-`src` imports) and confirm no other `src` modules are pulled in.

## 2. build_template.py rework

- [x] 2.1 Remove the `SKILL_SRC` constant and `_bootstrap()` from `src/build_template.py`; replace the skill-`src` `sys.path` insert with resolution of the bundled tooling beside `build.py` (relative package import or local `sys.path` insert of the script dir).
- [x] 2.2 Rewrite the module docstring to document the uv workflow: the directory is a uv project, run `uv sync` once, then `uv run python build/build.py` (keep the `--plan`/`--parts-dir`/`--out`/`--orientations` flag docs); drop the `SKILL_SRC`/skill-moved-or-uninstalled text.
- [x] 2.3 Confirm `build.py`'s imports (`exporters._load_result`, `mesh_io.load_mesh`, `model_export.export_model`, `print_orientation.optimize_orientation`) resolve from the bundle layout chosen in 2.1.

## 3. SKILL.md Build phase

- [x] 3.1 Replace the `sed`/`Set-Content` `{{SKILL_SRC}}` substitution step (around SKILL.md:388-407) with: copy `build_template.py` verbatim to `build/build.py`, copy the bundled tooling closure from `$SKILL_DIR/src` into the working directory, and write `pyproject.toml` + `.python-version`.
- [x] 3.2 Add the `uv sync` step in the working directory, then a verification run `uv run python build/build.py`, after the tooling/files are in place.
- [x] 3.3 Update the Phase 4 delivery notes (SKILL.md:442) to point the user at `uv run python build/build.py` and note `uv.lock` is committed.

## 4. README

- [x] 4.1 Rewrite the "Regenerating the 3MF / STL files" section: describe the delivered working directory as a standalone uv project, show `uv sync` + `uv run python build/build.py`, and remove the paragraph about importing the skill's tooling from the baked `src/` path (README.md:69-70).

## 5. Tests & verification

- [x] 5.1 Update/extend tests covering `build_template.py` so they no longer assert the `SKILL_SRC` substitution and instead assert the bundled-tooling import path resolves.
- [x] 5.2 End-to-end check: scaffold a working directory via the Build phase, run `uv sync` + `uv run python build/build.py`, and confirm `model.3mf`, per-union STLs, per-plate STLs, and `uv.lock` are produced; spot-check it runs with the skill src/ off `PYTHONPATH`.
- [x] 5.3 Run `uv run pytest tests/` in the repo and `ruff check`/`ruff format` on changed Python files.
