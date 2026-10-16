## 1. Inventory

- [x] 1.1 Grep the whole repo (excluding `openspec/changes/archive/`, `documentation/DONE.md`, `TODO.md`) for `part frame|authored frame|assembled[- ]frame|print[- ]frame|build[- ]frame` and list hits per file
- [x] 1.2 Mark each `build frame` hit as build-pose or print-pose sense (known print-sense: `edge_treatment_check.py`, `quality_gate.py`, `fem_check.py`)

## 2. Docs and prompts

- [x] 2.1 Rewrite `SKILL.md:52-55` to build pose / assembly pose / print pose
- [x] 2.2 Update `CLAUDE.md` file-layout comments (`placement.py`, `edge_treatment_check.py`) to pose wording
- [x] 2.3 Update `README.md`, `FILES.md`, `ARCHITECTURE.md`, `reference/scripts.md`, `skill/*.md`
- [x] 2.4 Update `prompts/part.md`, `prompts/planning.md`, `prompts/audit.md`; confirm `render_prompt.py` output renders cleanly

## 3. Schema and inventory text

- [x] 3.1 Reword `description` strings in `src/build_plan_schema.json` (keep keys and structure)
- [x] 3.2 Reword `src/blocks/inventory.json` descriptions and `src/blocks/*.py` docstrings (`connectors.py`, `fasteners.py`, `print_frame.py`)

## 4. Source comments, docstrings, messages

- [x] 4.1 Reword docstrings/comments/CLI help in `src/` (`edge_treatment_check`, `quality_gate`, `print_orientation`, `fem_check`, `plan`, `write_assembly`, `placement`, `mate_chain`, `preview`, `run_cadquery_model`, `feature_presence_check`, `minimal_cutout_search`, `print_finishing`, `keep_out_check`, `deliverables`, `build_template`)
- [x] 4.2 Update user-facing message strings; update test expectations that assert on them (`test_edge_treatment_check`, `test_quality_gate`, `test_plan`, `test_fem_check`) and the `rim_fillet_fins.py.txt` fixture comment

## 5. Specs

- [x] 5.1 Reword retired terms in `openspec/specs/**` (~20 files); leave `coordinate-frame` untouched
- [x] 5.2 Run `openspec validate --all`

## 6. Guard and verify

- [x] 6.1 Add `tests/test_pose_terminology.py` scanning for retired phrases with the exempt paths from the spec
- [x] 6.2 Add the guard test to the `CLAUDE.md` test layout list
- [x] 6.3 Run `uv run pytest tests/` and `ruff check`; confirm no behavior change in JSON contract output
