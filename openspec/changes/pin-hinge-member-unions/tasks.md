## 1. Block: pin_hinge returns two member unions

- [ ] 1.1 In `src/blocks/joints.py`, change `pin_hinge` to build `part_a` (side-A leaf + knuckles)
      and `part_b` (side-B leaf + knuckles) separately, cut the shared coaxial `bore` from each, and
      `return {"leaf_a": part_a.cut(bore), "leaf_b": part_b.cut(bore)}` instead of the fused
      single-Workplane result. No geometry change -- each leaf is identical to today's within the
      fused body.

## 2. Retire hinge_leaf

- [ ] 2.1 In `src/blocks/joints.py`, delete the `hinge_leaf` function (and any now-unused helper it
      alone used).
- [ ] 2.2 In `src/blocks/__init__.py`, remove the `hinge_leaf` re-export.
- [ ] 2.3 In `src/blocks/inventory.json`, remove the `hinge_leaf` entry; confirm no `hinge_leaf` token
      remains under `src/` (grep).

## 3. Inventory + guidance

- [ ] 3.1 In `src/blocks/inventory.json`, update the `pin_hinge` `use` string to state it returns the
      two leaves `leaf_a` and `leaf_b` (so a hinge part declares `unions: [{"id":"leaf_a"},
      {"id":"leaf_b"}]`). Leave the `pin_hinge` `dof` (already the vector model) unchanged.
- [ ] 3.2 In `prompts/planning.md`, drop the `hinge_leaf` reference; in the kinematics example use
      `pin_hinge` with a moving union that is one of its leaves, and note a `pin_hinge` part declares
      its two leaf unions.

## 4. Tests

- [ ] 4.1 In `tests/test_blocks.py`, assert `pin_hinge(...)` returns a dict with exactly keys
      `{"leaf_a", "leaf_b"}`, each a watertight `cq.Workplane`; assert `hinge_leaf` is no longer
      importable from `blocks`; drop/replace the old `hinge_leaf` geometry tests.
- [ ] 4.2 Add a kinematic-check test: a print-in-place `pin_hinge` part with `unions:
      [leaf_a, leaf_b]` exports two unions and the sweep runs `leaf_a` against `leaf_b` (a
      leaf-vs-leaf collision at some angle is reported, or a clear sweep passes) -- proving the two
      leaves are now separate swept bodies rather than one frozen blob.
- [ ] 4.3 Update any test/fixture that imported or referenced `hinge_leaf`.

## 5. Verification

- [ ] 5.1 `uv run pytest tests/test_blocks.py tests/test_kinematic_check.py tests/test_plan_validate.py`
      pass.
- [ ] 5.2 `inventory.json` validates against the schema (no `hinge_leaf`; `pin_hinge` intact).
- [ ] 5.3 `ruff check` / `ruff format` clean on changed files; mypy and basedpyright clean on
      `src/blocks/joints.py`.
- [ ] 5.4 Confirm no `hinge_leaf` reference remains under `src/`, `prompts/`, or `tests/` (grep).
