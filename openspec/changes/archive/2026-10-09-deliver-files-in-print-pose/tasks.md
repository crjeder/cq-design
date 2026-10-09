## 1. Deliverables

- [x] 1.1 Add `_print_pose(asm, orientations, uid)` in `src/deliverables.py` (rotate `asm["authored"][uid]`; identity if no orientation) and use it in `_write_3mf`
- [x] 1.2 Export per-union STL from `_print_pose`; remove the copy from `assembly_dir`, set `union_stls_copied` False
- [x] 1.3 Export `step`/`obj`/`iges`/`scad` from `_print_pose`
- [x] 1.4 Update module/function docstrings and `build_template.py` summary text

## 2. Tests

- [x] 2.1 Test per-union STL bounding box matches rotated build pose and differs from assembly pose for a rotated union
- [x] 2.2 Test STEP/OBJ pose and no-orientation fallback to build pose
- [x] 2.3 Test assembly-dir meshes stay assembly pose after a build; copy part (`copy_of`) works

## 3. Docs

- [x] 3.1 Add build/assembly/print pose glossary and build-pose-directions rule to `CLAUDE.md`, `reference/scripts.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md`
- [x] 3.2 Run `uv run pytest tests/` and `openspec validate deliver-files-in-print-pose`
