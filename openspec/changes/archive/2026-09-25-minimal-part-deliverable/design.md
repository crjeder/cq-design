## Context

Part scripts are plain CadQuery files: `import cadquery as cq`, optionally `from cq_verify import ...`, `from blocks import ...`, and `cq_compat`, ending with a `result` Workplane (or a dict of them). The generated project ships `lib/` with the full tooling because `build/build.py` needs it for plates and exports. A user who only wants the parametric part does not need mesh/export/orientation code or trimesh/matplotlib/scipy. `blocks/` submodules import only cadquery (cq_warehouse lazily inside `heat_set_boss`), and `blocks/__init__.py` re-exports every submodule, so the package copies as a unit.

## Goals / Non-Goals

**Goals:**
- One command produces `standalone/`: each part script, plus only the helper modules it imports, plus a cadquery-only `pyproject.toml`.
- Scripts run unmodified: `python <part_id>.py` from inside `standalone/` (helpers sit next to them on `sys.path`).

**Non-Goals:**
- Inlining block functions into the part script (single-file output).
- STL/3MF export or print orientation in the standalone (that stays the full bundle's job).
- Rewriting or pruning `blocks/`.

## Decisions

- **AST import scan, not a hard-coded list.** `ast.parse` each script, collect top-level import names, intersect with the known helpers (`cq_verify`, `cq_compat`, `blocks`). Adding a helper later is one tuple entry in `bundle_project.py`'s neighbourhood; unknown imports are left to the user's environment. Alternative (always ship everything) is what `lib/` already is.
- **Copy `blocks/` whole when imported.** Pruning submodules would need a rewritten `__init__`; the package is ~75 KB and is cadquery-only, so the saving is not worth the divergence from `src/blocks`. A part importing only `cq_verify` ships with one 1-file helper.
- **Transitive helpers.** If a copied helper imports another (e.g. `cq_verify` -> none today), the scan repeats over copied modules until stable. Cheap guard so a future helper import does not silently break the standalone.
- **Separate `pyproject.toml`, cadquery only.** `cq-warehouse` is added only when a script (or copied `blocks/`) needs it; since `heat_set_boss` imports it lazily, it is added only when a part script imports `cq_warehouse` directly or calls `heat_set_boss`. Simplest rule: add it when the text `cq_warehouse` or `heat_set_boss` appears in any shipped .py.
- **Also copy `parameters.py`** if present at the project root, so the sourced-measurement provenance travels with the code.
- **Output location `standalone/` in the project root**, regenerated (overwritten) each delivery, like `README.md`.

## Risks / Trade-offs

- [A part script imports a module not in the helper set] -> left unresolved by design; README lists the imports the scan saw outside cadquery so the user knows.
- [`standalone/` drifts from `build/`] -> regenerated on every Phase 4 delivery, and copies are overwritten, never merged.
- [Full `blocks/` shipped for a one-function use] -> accepted, see above.
