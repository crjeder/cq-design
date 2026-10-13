## 1. Graph classification

- [x] 1.1 Change `_bfs_mate_tree` in `src/plan.py` to track edges by joint index and return the spanning-tree parent map plus the list of closure edges (including second joints between the same pair)
- [x] 1.2 In `_check_joints`, resolve each joint's block `dof` from the inventory; reject (conflicting mate path) any cycle containing a `dof` edge, and accept cycles of rigid edges only

## 2. Closure check

- [x] 2.1 Add a residual helper in `src/mate_chain.py` using `placement.to_matrix` (lazy numpy import) returning translation mm and rotation deg
- [x] 2.2 In `_check_joints`, derive spanning-tree poses (reuse `compute_mate_poses` logic) and emit a blocking error per closure edge over 0.01 mm / 0.01 deg, naming `joint_id`, both parts, and residuals

## 3. Tests

- [x] 3.1 Update the existing cycle test in `tests/test_plan.py` (three pin_hinge joints) to still assert "conflicting mate path"
- [x] 3.2 Add a four-part `dovetail_corner_joint` ring with consistent docks: validates clean, and `compute_mate_poses` equals the spanning-tree poses
- [x] 3.3 Add a ring with one dock off by 2 mm: error names the joint and ~2 mm residual
- [x] 3.4 Add a duplicate-pair joint with disagreeing docks: closure error; with agreeing docks: passes
- [x] 3.5 Add a mixed ring (rigid edges plus one `pin_hinge`): rejected

## 4. Docs

- [x] 4.1 Update `root_part`/`joints` descriptions in `src/build_plan_schema.json` and any "single tree" wording in `prompts/planning.md`, `skill/phase2_planning.md`, `reference/scripts.md`
- [x] 4.2 Mark the TODO.md "HitsterTower dovetail form" item as resolved by this change, noting the tower migration is a follow-up eval case
- [x] 4.3 Run `uv run pytest tests/test_plan.py tests/test_templates.py` and `openspec validate rigid-joint-loops`
