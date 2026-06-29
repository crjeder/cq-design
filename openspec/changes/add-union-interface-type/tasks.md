## 1. Vocabulary

- [ ] 1.1 Add `"union"` to the interface `type` enum in `src/blocks/inventory_schema.json` (the `interfaces.items.properties.type.enum` array), and extend the `type` description (or add a one-line gloss) noting `union` = fused into the parent part's body, vs mating docks vs kinematic axes.
- [ ] 1.2 Add `"union"` to `_VALID_INTERFACE_TYPES` in `src/blocks/validate.py` so the validator and schema agree.

## 2. Guidance

- [ ] 2.1 Add a short note to `prompts/planning.md` (next to the existing interface guidance) on choosing the interface type: `union` for a block fused into the same rigid body, a mating dock (`face_mount`, etc.) for a join to a separately printed part, and a kinematic axis (`hinge_axis`, etc.) for a moving joint.

## 3. Tests

- [ ] 3.1 In `tests/test_blocks.py`, assert a minimal block descriptor with `{"type": "union", "orientation": "+Z", "origin": [0, 0, 0]}` passes `validate_inventory` (no error), and that an unknown type (e.g. `"glue_tab"`) still fails.
- [ ] 3.2 Assert the shipped `inventory.json` still validates after the vocabulary change (regression guard).

## 4. Verification

- [ ] 4.1 `uv run pytest tests/test_blocks.py tests/test_plan_validate.py` pass.
- [ ] 4.2 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on `src/blocks/validate.py`.
- [ ] 4.3 Remove the resolved `interface` `union` line from `TODO.md` (lines 18-19); leave the separate "`hinge_axis` is too narrow" generalization noted as its own future item if still wanted.
