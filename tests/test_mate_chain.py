"""Tests for mate-chain pose derivation (`mate_chain.compute_mate_poses`)."""

import numpy as np

from mate_chain import compute_mate_poses
from placement import to_matrix


def _plan(parts, joints, root_part):
    return {"parts": parts, "root_part": root_part, "joints": joints}


def _hinge(joint_id, part_a, dock_a, part_b, dock_b):
    member_a = {"member": "leaf_a", "part": part_a}
    if dock_a is not None:
        member_a["dock"] = dock_a
    member_b = {"member": "leaf_b", "part": part_b}
    if dock_b is not None:
        member_b["dock"] = dock_b
    return {
        "joint_id": joint_id,
        "block": "pin_hinge",
        "params": {},
        "members": [member_a, member_b],
    }


def test_no_joints_returns_empty():
    plan = {"parts": [{"id": "solo"}]}
    assert compute_mate_poses(plan) == {}


def test_two_part_chain_derives_expected_transform():
    # door is root (identity placement); wall's dock offsets leaf_b by +10mm in Z
    # within wall's own frame, so wall's world pose must be -10mm in Z to bring
    # leaf_b back to where leaf_a (door, identity dock) landed in the world.
    dock_b = {"translate_mm": [0, 0, 10]}
    plan = _plan(
        parts=[{"id": "door"}, {"id": "wall"}],
        joints=[_hinge("h1", "door", None, "wall", dock_b)],
        root_part="door",
    )
    poses = compute_mate_poses(plan)
    assert set(poses) == {"wall"}
    expected = to_matrix({"translate_mm": [0, 0, -10]})
    np.testing.assert_allclose(poses["wall"], expected, atol=1e-9)


def test_three_part_chain_composes_root_mid_leaf():
    dock_b1 = {"translate_mm": [0, 0, 5]}
    dock_b2 = {"translate_mm": [1, 0, 0]}
    dock_c2 = {"translate_mm": [0, 2, 0]}
    plan = _plan(
        parts=[{"id": "a"}, {"id": "b"}, {"id": "c"}],
        joints=[
            _hinge("h1", "a", None, "b", dock_b1),
            _hinge("h2", "b", dock_b2, "c", dock_c2),
        ],
        root_part="a",
    )
    poses = compute_mate_poses(plan)
    assert set(poses) == {"b", "c"}
    np.testing.assert_allclose(poses["b"], to_matrix({"translate_mm": [0, 0, -5]}), atol=1e-9)
    np.testing.assert_allclose(poses["c"], to_matrix({"translate_mm": [1, -2, -5]}), atol=1e-9)


def test_part_outside_mate_graph_is_absent():
    plan = _plan(
        parts=[{"id": "door"}, {"id": "wall"}, {"id": "standalone"}],
        joints=[_hinge("h1", "door", None, "wall", {"translate_mm": [0, 0, 1]})],
        root_part="door",
    )
    poses = compute_mate_poses(plan)
    assert "standalone" not in poses
    assert "door" not in poses  # root itself is not included


def test_root_part_own_placement_seeds_the_chain():
    plan = _plan(
        parts=[
            {"id": "door", "placement": {"translate_mm": [100, 0, 0]}},
            {"id": "wall"},
        ],
        joints=[_hinge("h1", "door", None, "wall", None)],
        root_part="door",
    )
    poses = compute_mate_poses(plan)
    np.testing.assert_allclose(poses["wall"], to_matrix({"translate_mm": [100, 0, 0]}), atol=1e-9)
