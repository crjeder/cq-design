## 1. Schema

- [x] 1.1 Add `seam` to the interface `type` enum in `src/blocks/inventory_schema.json`
      (also added to the runtime vocabulary in `src/blocks/validate.py`)
- [x] 1.2 Confirm existing `inventory.json` still validates against the updated schema

## 2. Implementation (`src/blocks/joints.py`)

- [x] 2.1 Add `filament_hinge(length, knuckles, leaf_w, leaf_t, d_filament=1.9, clearance=0.25)`:
      reuse `_cylinder_along_y` for alternating A/B knuckle bands, place both flat leaves
      coplanar on opposite sides of the axis, bore one coaxial `d_filament` through-hole
      (a connecting tab fuses each leaf to its own knuckles since a bare tangent does not
      merge in OCC)
- [x] 2.2 Add `living_hinge(length, panel_w, panel_t, web_t=0.6, web_w=2.0)`:
      two panels bridged by a thin continuous web flush with one face
- [x] 2.3 Add `shadow_gap(length, wall, overlap=3.0)`: additive return-lip bar from Y=0
      to Y=`overlap` (reveal/clearance are a two-part placement relationship, kept in the
      docstring rather than as unused parameters)
- [x] 2.4 Write each function's docstring including print orientation / material caveat
      (living hinge) and the back-member placement contract (shadow gap)

## 3. Exports and inventory

- [x] 3.1 Re-export `filament_hinge`, `living_hinge`, `shadow_gap` from `src/blocks/__init__.py`
- [x] 3.2 Add `filament_hinge` descriptor to `inventory.json`
      (`motion: hinge`, `reversible: true`, `carries: ["shear-xy"]`, `hinge_axis` +Y)
- [x] 3.3 Add `living_hinge` descriptor to `inventory.json`
      (`motion: hinge`, `reversible: false`, `carries: ["shear-xy"]`, `hinge_axis` +Y)
- [x] 3.4 Add `shadow_gap` descriptor to `inventory.json`
      (`motion: rigid`, `reversible: true`, `carries: ["lock-z"]`, `seam` +Y)

## 4. Tests (`tests/test_blocks.py`)

- [x] 4.1 `filament_hinge`: two interleaved leaf solids; coaxial `d_filament` bore is
      hollow; leaves on opposite sides of the axis; wider `clearance` removes more material
- [x] 4.2 `living_hinge`: one watertight solid; web region thickness < `panel_t`; web spans full length
- [x] 4.3 `shadow_gap`: lip solid is `length` x `wall` and extends Y=0..`overlap`; unions watertight
- [x] 4.4 Inventory validation passes for all new entries (including the `seam` interface)

## 5. Verify

- [x] 5.1 `uv run python -m pytest tests/test_blocks.py tests/test_plan_validate.py` (81 passed)
- [x] 5.2 `ruff check --fix` and `ruff format` on changed files (all checks passed)
