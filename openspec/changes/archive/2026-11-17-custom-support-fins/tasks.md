## 1. Reference and plan schema

- [x] 1.1 Write `reference/support_fins.md`: dimension table with provenance (Slant3D via support-fins `FIN-SPEC.md`), "unverified on printer" note
- [x] 1.2 Add optional `sacrificial` (union) and `constraints.fin_hints` (default true) booleans to the plan schema; test that an old plan still validates in `tests/test_plan.py`

## 2. Fin block

- [x] 2.1 Implement `breakaway_fin` plus probe in `src/blocks/supports.py` (wall, standoff, tines, rounded top, optional bed pad, typed errors incl. `fin_collision`)
- [x] 2.2 Register `breakaway_fin` in `src/blocks/inventory.json` and export it from `src/blocks/__init__.py`
- [x] 2.3 Write `tests/test_supports_block.py`: tine span/height, rounded top, tine count scaling, invalid params, collision error, inventory schema validation

## 3. Placement script

- [x] 3.1 Implement `src/fin_placement.py` reusing `mesh_io` overhang regions and bridge detection; JSON contract `success/errors/fins`
- [x] 3.2 Write `tests/test_fin_placement.py`: overhang suggestion, self-supporting part, bridge skipped, no file modification

## 4. Gate and export integration

- [x] 4.1 `quality_gate.py`: skip `sacrificial` unions in overhang, sliver_fin, thin-region and brim checks; emit one `designed_support` info issue; emit a `fin_hint` info issue after `overhang_exceeded` unless `constraints.fin_hints` is false
- [x] 4.2 `estampo_export.py`: write `enable_support = false` for parts with a sacrificial union
- [x] 4.3 Extend gate and estampo tests for the new findings and export key

## 5. Docs and cleanup

- [x] 5.1 Add `FILES.md` lines and `reference/scripts.md` contract entries for `fin_placement.py` and `blocks/supports.py`; mention the block in `skill/phase3_build.md` block guidance
- [x] 5.2 Run `uv run pytest tests/` and `ruff check` / `ruff format` on changed files
- [x] 5.3 Remove the "Custom support" item from `TODO.md` section 8 (or link the archived change)
