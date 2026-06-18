"""Tests for the kinematic range-of-motion validation stage.

Fixtures use trimesh-generated box STLs (no CadQuery) so the suite stays fast.
A moving box orbits a Z axis at the origin; a fixed box is placed either clear of
or inside the swept arc to exercise the collision-free and binding paths.
"""

import json
import sys

import pytest
import trimesh

import kinematic_check
from kinematic_check import iter_poses, run_kinematic_check
from plan_validate import validate_plan


def _box_stl(path, extents, center):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    mesh.export(str(path))


def _revolute_entry(required_range, step=5, fixed="base", moving="arm"):
    return {
        "joint_id": "j1",
        "moving_part": moving,
        "fixed_part": fixed,
        "block": "hinge_leaf",
        "axis_origin_mm": [0, 0, 0],
        "axis_dir": "Z",
        "type": "revolute",
        "required_range": required_range,
        "unit": "deg",
        "step": step,
    }


@pytest.fixture
def clear_stls(tmp_path):
    """Fixed box well outside the moving box's orbit -> collision-free sweep."""
    _box_stl(tmp_path / "base.stl", (10, 10, 10), (0, 0, 0))
    _box_stl(tmp_path / "arm.stl", (10, 10, 10), (20, 0, 0))
    return tmp_path


@pytest.fixture
def blocking_stls(tmp_path):
    """Fixed wall to the north that the orbiting arm swings into past ~60 deg."""
    _box_stl(tmp_path / "base.stl", (10, 10, 10), (0, 14, 0))
    _box_stl(tmp_path / "arm.stl", (10, 10, 10), (20, 0, 0))
    return tmp_path


# ---- 5.1 numeric within limit ------------------------------------------------


def test_required_range_within_limit_no_issue(clear_stls):
    plan = {"kinematics": [_revolute_entry([0, 90])]}
    issues = run_kinematic_check(plan, str(clear_stls))
    assert not [i for i in issues if i["type"] == "range_exceeds_limit"]


# ---- 5.2 numeric exceeds limit, without loading a mesh ------------------------


def test_required_range_exceeds_limit(clear_stls, monkeypatch):
    # If a mesh were loaded/swept, this would raise; the numeric check must short
    # circuit before that.
    monkeypatch.setattr(
        kinematic_check,
        "_sweep_collision",
        lambda *a, **k: pytest.fail("sweep must not run when range exceeds limit"),
    )
    plan = {"kinematics": [_revolute_entry([0, 270])]}  # hinge limit is [0, 180]
    issues = run_kinematic_check(plan, str(clear_stls))
    exceed = [i for i in issues if i["type"] == "range_exceeds_limit"]
    assert len(exceed) == 1
    assert exceed[0]["severity"] == "error"
    assert exceed[0]["mechanical_limit"] == [0, 180]


# ---- 5.3 collision-free sweep passes -----------------------------------------


def test_collision_free_sweep_passes(clear_stls):
    plan = {"kinematics": [_revolute_entry([0, 90])]}
    issues = run_kinematic_check(plan, str(clear_stls))
    assert not [i for i in issues if i["type"] == "motion_collision"]
    assert not [i for i in issues if i["severity"] == "error"]


# ---- 5.4 binding within range reported ---------------------------------------


def test_binding_within_range_reported(blocking_stls):
    plan = {"kinematics": [_revolute_entry([0, 90])]}
    issues = run_kinematic_check(plan, str(blocking_stls))
    collisions = [i for i in issues if i["type"] == "motion_collision"]
    assert len(collisions) == 1
    binding = collisions[0]["binding_value"]
    assert 0 < binding < 90  # binds mid-sweep, not at rest, not only at the end


# ---- 5.5 sweep is bounded to required_range ----------------------------------


def test_sweep_does_not_exceed_required_range():
    entry = _revolute_entry([0, 90], step=7)
    values = [v for v, _ in iter_poses(entry)]
    assert max(values) <= 90 + 1e-9
    assert values[0] == 0 and values[-1] == 90  # endpoints included


# ---- 5.6 fcl missing degrades gracefully -------------------------------------


def test_fcl_missing_skips_sweep_keeps_numeric_check(clear_stls, monkeypatch):
    monkeypatch.setitem(sys.modules, "fcl", None)  # `import fcl` -> ImportError
    plan = {"kinematics": [_revolute_entry([0, 270])]}  # also exceeds limit
    issues = run_kinematic_check(plan, str(clear_stls))
    skipped = [i for i in issues if i["type"] == "check_skipped"]
    assert len(skipped) == 1
    assert skipped[0]["severity"] == "warning"
    # numeric check still ran despite no collision backend
    assert any(i["type"] == "range_exceeds_limit" for i in issues)


# ---- 5.7 plan_validate cross-checks ------------------------------------------


def _write_plan(tmp_path, kinematics):
    plan = {
        "schema_version": 1,
        "intent": "kinematic validation fixture",
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "parts": [
            {
                "id": "base",
                "description": "base part",
                "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
                "interfaces": [],
                "blocks_needed": [],
            },
            {
                "id": "arm",
                "description": "arm part",
                "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
                "interfaces": [],
                "blocks_needed": [],
            },
        ],
        "assembly": {"strategy": "hinged", "clearance_mm": 0.3},
        "kinematics": kinematics,
        "constraints": {
            "wall_min_mm": 1.2,
            "overhang_max_deg": 45,
            "dimension_tolerance_mm": 0.3,
        },
    }
    path = tmp_path / "BUILD_PLAN.json"
    path.write_text(json.dumps(plan))
    return str(path)


def test_plan_validate_rejects_unknown_part(tmp_path):
    plan_path = _write_plan(tmp_path, [_revolute_entry([0, 90], moving="ghost")])
    errors = validate_plan(plan_path)
    assert any("moving_part 'ghost' is not a part id" in e for e in errors)


def test_plan_validate_rejects_unknown_block(tmp_path):
    entry = _revolute_entry([0, 90])
    entry["block"] = "no_such_block"
    plan_path = _write_plan(tmp_path, [entry])
    errors = validate_plan(plan_path)
    assert any("unknown block 'no_such_block'" in e for e in errors)


def test_plan_validate_rejects_block_without_dof(tmp_path):
    entry = _revolute_entry([0, 90])
    entry["block"] = "finger_joint"  # exists but carries no dof
    plan_path = _write_plan(tmp_path, [entry])
    errors = validate_plan(plan_path)
    assert any("has no 'dof' descriptor" in e for e in errors)


def test_plan_validate_rejects_unit_mismatch(tmp_path):
    entry = _revolute_entry([0, 90])
    entry["unit"] = "mm"  # hinge_leaf dof.unit is deg
    plan_path = _write_plan(tmp_path, [entry])
    errors = validate_plan(plan_path)
    assert any("does not match" in e and "dof.unit" in e for e in errors)
