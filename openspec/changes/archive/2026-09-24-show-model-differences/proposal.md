## Why

After a redesign or a post-delivery correction there is no way to see what actually changed between two versions of a model, so the user has to compare renders by eye. TODO.md line 30 asks for a 3D diff (prompted by the diff3d project: unchanged geometry gray, removed/added geometry in contrasting colors).

## What Changes

- Add `src/diff_models.py`, a CLI that takes two STL files and reports a JSON summary (volumes, bbox delta, removed/added volume) and optionally writes a diff preview PNG: common geometry gray, A-only red, B-only green.
- Computed with the existing trimesh + manifold3d + matplotlib stack; no new dependency. diff3d itself is not adopted (interactive GUI/pyvista, cannot be driven headless from the Claude session).
- No pipeline gate or phase wiring in this change; it is a standalone tool Claude or the user can call, e.g. between a delivered STL and its corrected rebuild.

## Capabilities

### New Capabilities
- `model-diff`: compare two meshes and report/render what was removed and added.

### Modified Capabilities

## Impact

- New: `src/diff_models.py`, `tests/test_diff_models.py`, `reference/scripts.md` entry, CLAUDE.md file-layout line, TODO.md line 30 checked off.
- Deps: none new (trimesh, manifold3d, matplotlib already declared).
