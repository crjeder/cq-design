## 1. Inventory schema

- [x] 1.1 Add optional `emits` (array of exactly 2 strings) to a block descriptor in
      `src/blocks/inventory_schema.json`, alongside the existing `dof`.
- [x] 1.2 Add `emits: ["leaf_a", "leaf_b"]` to `pin_hinge`'s entry in
      `src/blocks/inventory.json`.
- [x] 1.3 Add/extend `tests/test_blocks.py` (or the inventory validator's tests):
      `pin_hinge` validates with `emits`; a block descriptor with `emits` of the
      wrong length is rejected by the schema. (Also added the matching runtime
      check to `blocks/validate.py::validate_inventory`, since `inventory_schema.json`
      itself isn't wired into any runtime validation path.)

## 2. Build plan schema

- [x] 2.1 Promote the existing `placement` object to a named `definitions` entry
      (e.g. `definitions/placement`) in `src/build_plan_schema.json`, referenced by
      both a part's `placement` and a joint member's `dock` (same shape, two use
      sites) -- avoids duplicating the rotate/translate definition.
- [x] 2.2 Add optional top-level `joints` (array) and `root_part` (string) to
      `src/build_plan_schema.json`. Each `joints` item: `joint_id`, `block`,
      `params` (object), `members` (array, exactly 2 items, each
      `{member, part, dock?}` referencing `definitions/placement` for `dock`).
      `root_part` required when `joints` is non-empty (schema `if`/`then` on
      `joints` non-empty implying `required: ["root_part"]`).
- [x] 2.3 Validate the updated schema loads and passes `jsonschema.Draft7Validator.check_schema`.

## 3. Plan validation (`plan_validate.py`)

- [x] 3.1 Add `_check_joints(plan, inventory_path)`: for each `joints` entry, cross-check
      `block` exists and carries `emits`; each member's `member` is one of the
      block's two `emits` ids and the two members reference distinct ids; each
      member's `part` is an existing part id; the two members do not name the same
      part.
- [x] 3.2 In `_check_joints`, build the mate graph (parts as nodes, each `joints`
      entry as an edge) and validate against `root_part`: every part named in some
      `joints` entry is reachable from `root_part` via exactly one path (reject a
      second path as a conflicting mate path / cycle); a part in the graph not
      reachable from `root_part` is unanchored; a part reachable via the mate chain
      that also declares its own `placement` is double-anchored (`root_part`
      exempt).
- [x] 3.3 Wire `_check_joints` into `validate_plan`.
- [x] 3.4 Add `tests/test_plan_validate.py` cases: unknown block / block without
      `emits` rejected; unknown emits id rejected; duplicate emits id within one
      joint rejected; same-part members rejected; unanchored part rejected; cycle
      rejected; double-anchored part rejected; `root_part`'s own placement is not
      flagged; a plan with no `joints` needs no `root_part` and validates as before.

## 4. Pose derivation

- [x] 4.1 Add `src/mate_chain.py`: given a plan's `joints` and `root_part`, and each
      part's own `placement` (for `root_part`), compute and return a
      `dict[part_id, 4x4 transform]` for every part reachable via the mate chain,
      by walking outward from `root_part` and applying
      `world_pose(part_B) = world_pose(part_A) @ to_matrix(dock_A) @ inv(to_matrix(dock_B))`
      at each hop (reusing `placement.to_matrix`). (Also added `placement.apply_matrix`
      to position a CadQuery Workplane by a general 4x4 transform, since a derived
      mate-chain pose doesn't decompose back into `placement`'s ordered-rotation shape.)
- [x] 4.2 Add `tests/test_mate_chain.py`: a two-part chain derives the expected
      transform (numeric check against a hand-computed matrix for a simple
      rotate+translate `dock` pair); a three-part chain (root -> mid -> leaf)
      composes correctly; a part outside the mate graph is absent from the
      returned dict.

## 5. Model export integration

- [x] 5.1 In `src/model_export.py`, compute the mate-chain transforms once (via
      `mate_chain.py`) and use a mate-chain part's derived transform in place of
      reading its `placement` field, for every union that part produces.
- [x] 5.2 Add/extend `tests/test_exporters.py` (or a `model_export`-focused test):
      a two-part plan with one `joints` entry exports both unions positioned
      consistently with the derived mate-chain transform, not at their (absent)
      `placement`. (Added to `tests/test_model_export.py`, alongside a second test
      confirming a part outside the mate chain still uses its own `placement`.)

## 6. Docs

- [x] 6.1 Add `src/mate_chain.py` and the `joints`/`root_part` schema fields to the
      `CLAUDE.md` script table and file layout list.
- [x] 6.2 Note in `prompts/planning.md` that a matched-pair block's two members can
      be distributed across two parts via a `joints` entry instead of one part's
      `unions` array, with a pointer to when to use which.
