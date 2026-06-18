## Why

The block library already taxonomizes joints by `motion` (`hinge`, `ball`,
`rigid`), so the skill knows which parts are meant to move — but nothing verifies
that a joint actually achieves the motion the design depends on. A user who
specifies "the phone-holder arm folds 90 degrees from upright to flat" gets no
confirmation that the arm clears that arc without binding against the base. The
pipeline fuses each part to a single STL and exports separate STLs per part, but
performs no motion check at all. Bind points, lip interference, and
clearance-too-tight failures only surface after printing.

This adds a declared-range kinematic check: the author states the required range
of motion in `BUILD_PLAN.json`, the block declares its intrinsic degree of
freedom in the inventory, and a new analysis stage sweeps the moving part through
the declared range against the fixed part to confirm it is collision-free.

## What Changes

- Add a `dof` (degree of freedom) descriptor to joint entries in
  `blocks/inventory.json`: `type` (`revolute` | `prismatic` | `spherical` |
  `fixed`), local `axis`, `mechanical_limit` (the block's nominal full range), and
  `unit` (`deg` for revolute/spherical, `mm` for prismatic). The nominal limit is a
  sanity bound only; the geometry sweep is the source of truth for what the printed
  part actually achieves.
- Add a top-level `kinematics` array to `BUILD_PLAN.json` (and its schema): each
  entry declares a moving part, a fixed part, the joint block, the world-space
  joint axis (`axis_origin_mm` + `axis_dir`), the joint `type`, the
  `required_range` the design needs, its `unit`, and a sweep `step`.
- Add `src/kinematic_check.py`: a new analysis stage, sibling to the overhang
  analysis, that runs when the plan has at least one `kinematics` entry. For each
  joint it performs two checks: (1) `required_range` fits within the block's
  `mechanical_limit` (cheap, declared-vs-declared); (2) a collision sweep of the
  moving part's STL against the fixed part's STL through the required range using
  `trimesh.collision.CollisionManager` (geometry truth). It emits structured
  findings consistent with the existing `{type, message, hint, ...}` contract.
- The stage relies on `python-fcl` (required by trimesh's `CollisionManager`),
  already declared in `pyproject.toml` and locked. The stage still degrades to a
  `check_skipped` warning if the backend is unavailable at runtime.
- Wire the stage into the quality gate / Phase 3, gated on the presence of
  `kinematics` entries.

## Capabilities

### New Capabilities
- `kinematic-range-validation`: Declared-range motion validation. The author
  declares each joint's required range of motion in `BUILD_PLAN.json` and the
  block declares its intrinsic degree of freedom in the inventory; an in-process
  trimesh+fcl analysis stage verifies the required range is within the block's
  nominal limit and sweeps the moving part through that range against the fixed
  part to confirm it is collision-free, emitting structured findings and binding
  angle on failure.

## Impact

- **Code**: new `src/kinematic_check.py`; schema additions to
  `src/build_plan_schema.json` (`kinematics`) and `src/blocks/inventory_schema.json`
  (`dof`); inventory data updates for the revolute/prismatic/spherical joint blocks
  (`hinge_leaf`, `filament_hinge`, `dovetail_groove`/`dovetail_tongue`,
  `ball_stud`/`ball_socket`); a hook into the quality-gate / Phase 3 flow.
- **Dependencies**: `python-fcl` and `trimesh` already declared in
  `pyproject.toml` and locked. Implementation surfaced that trimesh's
  `CollisionManager` also requires `scipy` (via `is_convex`), which was not a
  dependency; `scipy>=1.10,<2` was added.
- **Docs**: `SKILL.md` (new analysis stage, plan `kinematics` field, inventory
  `dof` field), `CLAUDE.md` (script table row for `kinematic_check.py`).
- **Tests**: new `tests/test_kinematic_check.py` covering range-within-limit,
  range-exceeds-limit, collision-free sweep, binding-angle detection, and the
  fcl-missing skip path.

## Out of Scope

- **Print-in-place single-body joints** (`filament_hinge`, print-in-place
  `hinge_leaf` variant): these are a single fused STL with an internal degree of
  freedom, with no separate mesh to collide against without splitting the body by
  its leaf geometry. Deferred to a follow-up.
- **`living_hinge`**: a one-piece flexure that bends elastically with no rigid
  degree of freedom; it has no kinematic joint to validate and is excluded.
- **Dynamics**: gravity, torque, stability, motor simulation. This stage is purely
  kinematic (collision through a declared range), which is why trimesh+fcl is
  sufficient and PyBullet is not required.
