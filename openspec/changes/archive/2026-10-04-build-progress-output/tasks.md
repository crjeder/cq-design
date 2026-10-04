## 1. model_export

- [x] 1.1 Add keyword-only `progress: Callable[[str], None] | None = None` to `export_model`
- [x] 1.2 Emit `[k/N] loading <part-id>` per part in the load loop (`N` = number of plan parts)
- [x] 1.3 Emit `writing model.3mf` before the 3MF write
- [x] 1.4 Emit `[k/N] stl <union-id>` per union STL and `[k/N] plate <plate>` per fused plate (`N` known after the load loop)

## 2. build.py

- [x] 2.1 In `resolve_orientations`, pre-compute the set of unions needing computation (missing or stale entry) once, reuse it in the loop, and print `[k/N] orientation <union-id>` for each
- [x] 2.2 Pass `lambda s: print(s, flush=True)` as `progress` to `export_model`; leave `_print_summary` and the stderr failure message unchanged

## 3. Tests and docs

- [x] 3.1 `tests/test_model_export.py`: recording callback gets the expected numbered lines per phase; no callback prints nothing and writes identical files
- [x] 3.2 `tests/test_build_script.py`: stdout contains the `[k/N]` loading lines before the summary; reused orientations print no orientation lines; recomputed ones are numbered over the recomputed set only
- [x] 3.3 Update the README command-line reference to mention the progress lines, and `reference/scripts.md` if it documents the `export_model` signature
- [ ] 3.4 If `build-format-option` has landed, add a `[k/N] <fmt> <union-id>` line to its extra-formats loop
