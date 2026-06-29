## 0. Base

- [ ] 0.1 Branch on top of `add-union-interface-type` (PR #13) -- or off `main` once #13 has merged -- so the `block-library` closed-set and `union` requirements already carry the full vocabulary this change edits.

## 1. Vocabulary

- [ ] 1.1 In `src/blocks/inventory_schema.json`, replace `"hinge_axis"` with `"joint_axis"` in the interface `type` enum, and update the `type` description to use `joint_axis` (the motion-agnostic kinematic-axis reference; motion kind from the block's `dof.type`).
- [ ] 1.2 In `src/blocks/validate.py`, replace `"hinge_axis"` with `"joint_axis"` in `_VALID_INTERFACE_TYPES`.

## 2. Inventory migration

- [ ] 2.1 In `src/blocks/inventory.json`, change the interface `type` from `hinge_axis` to `joint_axis` on `hinge_leaf`, `pin_hinge`, and `living_hinge` (keep each interface's `orientation`/`origin` and the blocks' `dof`/`motion`/`reversible` unchanged).
- [ ] 2.2 Confirm no `hinge_axis` token remains anywhere under `src/` (grep).

## 3. Guidance

- [ ] 3.1 Update `prompts/planning.md` interface-type guidance to use `joint_axis` instead of `hinge_axis` in the kinematic-axis examples.

## 4. Tests

- [ ] 4.1 In `tests/test_blocks.py`, assert a descriptor with `{"type": "joint_axis", ...}` validates, and that `{"type": "hinge_axis", ...}` is now rejected as an unknown type.
- [ ] 4.2 Assert the shipped `inventory.json` still validates and declares no interface of `type: "hinge_axis"`.

## 5. Verification

- [ ] 5.1 `uv run pytest tests/test_blocks.py tests/test_kinematic_check.py` pass (the hinge/flex blocks are metadata-renamed only; geometry and kinematics are unchanged).
- [ ] 5.2 `inventory_schema.json` is valid JSON; `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on `src/blocks/validate.py`.
- [ ] 5.3 Tick the `hinge_axis` generalization item in `TODO.md`.
