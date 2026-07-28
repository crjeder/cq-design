## 1. Schema

- [x] 1.1 In `src/build_plan_schema.json`'s `kinematics_entry`, drop `"block"` from
      `required` and update its `description` to note the block-less case.
- [x] 1.2 Add an optional `mechanical_limit` property to `kinematics_entry` (`[lo, hi]`
      array, same shape as a block's `dof.mechanical_limit`), with a description noting
      it's meaningful only when `block` is absent and ignored when `block` is present.

## 2. Plan validation (`src/plan_validate.py`)

- [x] 2.1 In `_check_kinematics`, resolve `block_name = entry.get("block")` and skip the
      type/axis/coaxiality contract arms (`continue`) when it's `None`, keeping the
      `moving_union` union-id check unconditional.
- [x] 2.2 Update `_check_kinematics`'s docstring to state the contract arms apply only
      when `block` is present.

## 3. Kinematic check runner (`src/kinematic_check.py`)

- [x] 3.1 In `run_kinematic_check`, make block lookup conditional
      (`get_block(entry["block"], inventory_path) if entry.get("block") else None`) and
      derive `limit` from the block's `dof.mechanical_limit` when present, else
      `entry.get("mechanical_limit")`.
- [x] 3.2 When `limit` is `None`, emit a `range_check_not_applicable` warning issue
      (joint id, no mesh) instead of silently skipping the numeric check, and fall
      through to the collision sweep unchanged.
- [x] 3.3 When `limit` is not `None`, run the existing `range_exceeds_limit` check
      against it (block or entry sourced) exactly as today.
- [x] 3.4 Update the module docstring and `run_kinematic_check`'s docstring to describe
      the block-less path.

## 4. Tests (`tests/test_plan_validate.py`, `tests/test_run_evals.py` if applicable)

- [x] 4.1 Add a test: a block-less entry (no `block`) with valid `moving_union`/axis
      fields validates with no contract-related error.
- [x] 4.2 Add a test: a block-less entry with a bad `moving_union` still fails with
      the existing "is not a union id" error.
- [x] 4.3 Add a test: a block-backed entry is unaffected -- existing contract tests
      (`test_contract_*`) still pass unmodified.
- [x] 4.4 Add a `kinematic_check.py` test (or extend an existing one) covering: (a) a
      block-less entry with `mechanical_limit` gets `range_exceeds_limit` when out of
      range, (b) a block-less entry with no `mechanical_limit` gets
      `range_check_not_applicable` and still sweeps.

## 5. Planner guidance

- [x] 5.1 `prompts/planning.md` rule 9: add a sentence that a custom/raw-primitive
      joint omits `block` and declares `mechanical_limit` directly if wanted, and
      never omits the whole `kinematics` entry for lack of a matching block.
- [x] 5.2 `skill/phase3_build.md`'s "Kinematic validation" section: add a short
      block-less example next to the existing block-backed one, citing the
      phone-holder retrospective's omitted-entry choice as the anti-pattern removed.

## 6. Documentation and tracking

- [x] 6.1 `CLAUDE.md`: update the `plan_validate.py` / `kinematic_check.py` table row
      wording so "referenced block exists, carries a `dof`" reads as conditional on
      `block` being present.
- [x] 6.2 `TODO.md`: mark part (a) of the "kinematics for custom (block-free) hinges"
      sub-item done.

## 7. Verification

- [x] 7.1 Run `uv run pytest tests/test_plan_validate.py` and any updated
      `kinematic_check` tests; confirm the full suite still passes.
- [x] 7.2 Run `openspec validate blockless-kinematics --strict` to confirm the specs
      delta still validates after any wording tweaks made during implementation.
