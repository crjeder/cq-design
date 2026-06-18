## 1. Implement the block

- [x] 1.1 Add `teardrop_bore(d, depth, angle=45)` to `src/blocks/connectors.py`: build the cross-section wire as a lower circular arc (radius `d/2`) plus two straight roof faces meeting at an apex on the vertical centerline, then extrude along +Y by `depth + _EPS`.
- [x] 1.2 Compute the apex height from `d/2` and `angle` (default 45 deg = apex one radius above center); ensure the apex is at max Z so the peak points up.
- [x] 1.3 Add a one-line docstring and a `use`-style note stating the block is for horizontal bores only and that the peak points +Z (part must print in that orientation).

## 2. Register and export

- [x] 2.1 Add a `teardrop_bore` descriptor to `src/blocks/inventory.json` (module `blocks.connectors`, params for `d`/`depth`/`angle`, one `axis` interface oriented along the bore).
- [x] 2.2 Re-export `teardrop_bore` from `src/blocks/__init__.py` (import line, `__all__`, and the usage docstring at the top).

## 3. Tests

- [x] 3.1 Add a test in `tests/test_blocks.py` (or `tests/test_connectors.py` if present) asserting `teardrop_bore` returns a watertight solid and that subtracting it from a wall of thickness `depth` yields a watertight body.
- [x] 3.2 Add a test asserting the upper profile is a peak: the apex is at max Z and no upper face is a circular arc (e.g. check the topmost vertex/face and that the cross-section is not a plain cylinder).
- [x] 3.3 Add a test asserting the roof faces stay within the 45-degree overhang limit at the default angle.
- [x] 3.4 Add an inventory test (or extend the existing inventory/import test) confirming `teardrop_bore` is present and importable via `from blocks import teardrop_bore`.

## 4. Docs and validation

- [x] 4.1 Update `reference/FDM 3D Print Design Guidelines.md` so the "Horizontal holes -> consider teardrop shape" line points to the `teardrop_bore` block.
- [x] 4.2 Run `uv run pytest tests/test_blocks.py` (and inventory/import tests) and confirm all pass.
- [x] 4.3 Run `ruff check --fix` and `ruff format` on the changed Python files.
