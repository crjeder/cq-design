## 1. Implement the detector

- [x] 1.1 Add `_find_fillet_after_chamfer(tree, parents)` to `src/script_lint.py`,
      mirroring `_find_shell_after_fillet`: walk the AST, and for each
      `.fillet(...)` call, flatten its chain and check whether `.chamfer`
      appears earlier in the same chain; emit a `fillet_after_chamfer` finding
      with `line`/`message`/`hint` if so.
- [x] 1.2 Wire the new check into `lint_script`'s findings list.

## 2. Tests

- [x] 2.1 Add a `tests/test_script_lint.py` case: chamfer then fillet in one
      chain triggers `fillet_after_chamfer`.
- [x] 2.2 Add a clean-order case: fillet then chamfer in one chain produces no
      finding.
- [x] 2.3 Add a single-call case (only fillet, or only chamfer) producing no
      finding.
- [x] 2.4 Run `uv run pytest tests/test_script_lint.py` and confirm pass.

## 3. Docs

- [x] 3.1 Update `skill/phase3_build.md` Step 2.5's finding list to mention
      `.fillet()` after `.chamfer()`.
- [x] 3.2 Update `TODO.md` line 6 to point at this change instead of the
      edge-treatment rule it was prematurely marked against.
