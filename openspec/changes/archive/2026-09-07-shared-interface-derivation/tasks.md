## 1. Advisory check

- [x] 1.1 Add `check_shared_interfaces(plan) -> list[str]` to `src/plan_validate.py`:
      collect `interfaces[].name` per part (skip unnamed), keep names held by two or
      more parts, drop a pair covered by a `joints` entry whose two `members[].part`
      are those two parts, and emit one finding per remaining name listing the parts
      and pointing at `joints` / `mate_chain.py`.
- [x] 1.2 Print the findings from `main()` after `BUILD_PLAN OK`, following the
      `check_block_thinness` / `check_deferred_axis_arms` block shape.
- [x] 1.3 Confirm `validate_plan`'s returned error list is unchanged (the finding
      must not reach the quality gate's `plan_invalid` path).

## 2. Tests (`tests/test_plan_validate.py`, no CadQuery)

- [x] 2.1 Two parts share an interface name, no `joints` entry -> one finding naming
      both parts.
- [x] 2.2 Same, with a `joints` entry linking exactly those two parts -> no finding.
- [x] 2.3 A name on one part only, and interfaces with no `name` -> no finding.
- [x] 2.4 Three parts share a name with one joint covering two of them -> one
      finding naming the unlinked part.
- [x] 2.5 A plan that triggers the finding still returns `[]` from `validate_plan`.

## 3. Planner guidance

- [x] 3.1 `prompts/planning.md` rule 7: one sentence stating that reusing one
      `interfaces[].name` on two parts with no `joints` entry between them raises a
      plan-validation finding, and that a shared mate belongs in `joints` so the
      value has a single source.

## 4. Spec

- [x] 4.1 Sync the `joint-mate-entity` delta into `openspec/specs/joint-mate-entity/`.
- [x] 4.2 Archive the change.
