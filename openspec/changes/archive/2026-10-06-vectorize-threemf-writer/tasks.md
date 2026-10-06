## 1. Writer

- [x] 1.1 Rewrite `_weld` in `src/exporters/threemf_multi.py` with `np.unique`, preserving first-seen vertex order and original (unrounded) coordinates
- [x] 1.2 Replace per-element `ET.SubElement` vertex/triangle emission in `_add_object` with joined f-strings
- [x] 1.3 Compute non-manifold edge count from welded arrays in `_add_object`; return it from `write_named_3mf` and `write_single_3mf` (sum over objects)

## 2. Caller

- [x] 2.1 In `src/deliverables.py`, use `write_named_3mf`'s return value for the RuntimeError guard; drop the `count_nonmanifold_edges` re-parse and its `ImportError` fallback (keep the import-free path clean)

## 3. Tests

- [x] 3.1 Add test: new `_weld` output equals the old dict-loop result (vertex order + triangle indices) on a tessellated box and cylinder
- [x] 3.2 Add test: `write_named_3mf` returns 0 for a closed solid and equals `count_nonmanifold_edges(path)`
- [x] 3.3 Run `uv run pytest tests/test_exporters.py tests/test_assembly_and_deliverables.py` and `ruff check` / `ruff format` on changed files

## 4. Bookkeeping

- [x] 4.1 Tick TODO.md Optimisation item 8
