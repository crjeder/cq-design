## 0. Dependency

- [x] 0.1 `python-fcl>=0.7.0.11` and `scipy>=1.10,<2` declared in `pyproject.toml`
      and locked; verified `import fcl` + `CollisionManager` work (python-fcl
      0.7.0.11, trimesh 4.12.2). scipy is required transitively by trimesh's
      `CollisionManager` (`is_convex`) and was not previously a dependency.

## 1. Schema additions

- [x] 1.1 Add the `dof` object to `src/blocks/inventory_schema.json`: `type`
      (enum `revolute`/`prismatic`/`spherical`/`fixed`), `axis` (enum `X`/`Y`/`Z`),
      `mechanical_limit` (2-element number array), `unit` (enum `deg`/`mm`); mark it
      optional (`additionalProperties` already governs the items object)
- [x] 1.2 Add the `kinematics` array to `src/build_plan_schema.json` with required
      entry fields `joint_id`, `moving_part`, `fixed_part`, `block`,
      `axis_origin_mm` (3-element array), `axis_dir` (enum `X`/`Y`/`Z`), `type`,
      `required_range` (2-element array), `unit` (enum `deg`/`mm`), `step` (number);
      keep the array optional
- [x] 1.3 Extend `src/plan_validate.py` cross-checks: every `kinematics` entry's
      `moving_part`/`fixed_part` must reference existing part ids, `block` must
      exist in the inventory and carry a `dof`, and the entry `unit` must equal the
      block's `dof.unit`

## 2. Inventory data

- [x] 2.1 Add `dof` to `hinge_leaf` (revolute, axis `Y`, `[0, 180]`, `deg`)
- [x] 2.2 Add `dof` to `dovetail_groove` / `dovetail_tongue` (prismatic, axis `Y`,
      travel in `mm` per the groove length convention)
- [x] 2.3 Add `dof` to `ball_stud` / `ball_socket` (spherical, axis `Z`, cone range
      in `deg`)
- [x] 2.4 Leave `living_hinge` and the print-in-place `filament_hinge` without
      `dof` (out of scope per proposal)

## 3. Analysis stage (`src/kinematic_check.py`)

- [x] 3.1 Load the plan; if `kinematics` is absent or empty, exit reporting no
      findings (stage skipped)
- [x] 3.2 For each entry, run the numeric check: `required_range` within the
      block's `dof.mechanical_limit`; emit `range_exceeds_limit` on failure
- [x] 3.3 Guard the collision backend import (`fcl`); on ImportError emit a single
      `check_skipped` warning and skip only the sweep (numeric check still runs)
- [x] 3.4 Load `moving_part` and `fixed_part` STLs with trimesh; build a
      `CollisionManager` holding the fixed part
- [x] 3.5 Build the per-step transform: revolute -> `rotation_matrix(theta,
      axis_dir, axis_origin_mm)`; prismatic -> translation of `d` along `axis_dir`;
      iterate `required_range` by `step` including both endpoints
- [x] 3.6 At each step, apply the transform to the moving mesh and query collision;
      record the first colliding step as `binding_value`; emit `motion_collision`
      with `binding_value` and the required end value when binding occurs
- [x] 3.7 Emit all findings with the standard `{source, severity, type, message,
      hint, ...}` contract; report a clean pass when no issues
- [x] 3.8 Spherical sweep: v1 samples the cone boundary up to the required
      half-angle; document the coarseness in a module comment

## 4. Pipeline wiring

- [x] 4.1 Invoke `kinematic_check.py` from the quality gate / Phase 3 flow, gated
      on the plan having at least one `kinematics` entry, after parts are exported
      in deliver mode (separate STLs available)
- [x] 4.2 Fold its findings into the gate's aggregated issue list / report

## 5. Tests (`tests/test_kinematic_check.py`)

- [x] 5.1 `required_range` within `mechanical_limit` -> no `range_exceeds_limit`
- [x] 5.2 `required_range` outside `mechanical_limit` -> `range_exceeds_limit`
      emitted without loading a mesh
- [x] 5.3 Two simple part fixtures whose declared range is collision-free -> clean
      pass, no `motion_collision`
- [x] 5.4 Fixtures that interfere mid-range -> `motion_collision` with the correct
      `binding_value`
- [x] 5.5 Sweep bound: assert no position beyond `required_range[1]` is evaluated
      even when `mechanical_limit` is larger
- [x] 5.6 fcl-import-missing (monkeypatch) -> single `check_skipped` warning, no
      raise, numeric check still runs
- [x] 5.7 `plan_validate.py` rejects a `kinematics` entry referencing an unknown
      part, an unknown block, a block lacking `dof`, or a mismatched `unit`

## 6. Documentation

- [x] 6.1 `SKILL.md`: document the new analysis stage, the plan `kinematics` field,
      and the inventory `dof` field
- [x] 6.2 `CLAUDE.md`: add the `src/kinematic_check.py` row to the core-scripts
      table and note the `python-fcl` dependency
