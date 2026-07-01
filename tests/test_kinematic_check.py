"""Tests for the whole-model kinematic range-of-motion validation stage.

Fixtures use trimesh-generated box STLs (no CadQuery) so the suite stays fast.
A moving box orbits a Z axis at the origin; other unions are placed either clear of
or inside the swept arc to exercise the collision-free and binding paths. STLs are
assembled-pose per-union meshes (as the model export would emit).
"""

import json
import sys

import pytest
import trimesh

import kinematic_check
from kinematic_check import _sweep_values, iter_poses, run_kinematic_check
from plan_validate import validate_plan


def _box_stl(path, extents, center):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    mesh.export(str(path))


def _revolute_entry(required_range, step=5, moving="arm", **extra):
    entry = {
        "joint_id": "j1",
        "moving_union": moving,
        "block": "pin_hinge",
        "axis_origin_mm": [0, 0, 0],
        "axis_dir": "Z",
        "type": "revolute",
        "required_range": required_range,
        "step": step,
    }
    entry.update(extra)
    return entry


def _plan(kinematics, part_ids=("base", "arm")):
    """Minimal plan: run_kinematic_check only reads part ids and kinematics."""
    return {"parts": [{"id": p} for p in part_ids], "kinematics": kinematics}


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


# ---- numeric within limit ----------------------------------------------------


def test_required_range_within_limit_no_issue(clear_stls):
    issues = run_kinematic_check(_plan([_revolute_entry([0, 90])]), str(clear_stls))
    assert not [i for i in issues if i["type"] == "range_exceeds_limit"]


# ---- numeric exceeds limit, without loading a mesh ---------------------------


def test_required_range_exceeds_limit(clear_stls, monkeypatch):
    monkeypatch.setattr(
        kinematic_check,
        "_sweep_collision",
        lambda *a, **k: pytest.fail("sweep must not run when range exceeds limit"),
    )
    plan = _plan([_revolute_entry([0, 270])])  # hinge limit is [0, 180]
    issues = run_kinematic_check(plan, str(clear_stls))
    exceed = [i for i in issues if i["type"] == "range_exceeds_limit"]
    assert len(exceed) == 1
    assert exceed[0]["severity"] == "error"
    assert exceed[0]["mechanical_limit"] == [0, 180]


# ---- collision-free sweep passes ---------------------------------------------


def test_collision_free_sweep_passes(clear_stls):
    issues = run_kinematic_check(_plan([_revolute_entry([0, 90])]), str(clear_stls))
    assert not [i for i in issues if i["type"] == "motion_collision"]
    assert not [i for i in issues if i["severity"] == "error"]


# ---- 7.2 binding within range reported, naming the collider -------------------


def test_binding_within_range_names_collider(blocking_stls):
    issues = run_kinematic_check(_plan([_revolute_entry([0, 90])]), str(blocking_stls))
    collisions = [i for i in issues if i["type"] == "motion_collision"]
    assert len(collisions) == 1
    binding = collisions[0]["binding_value"]
    assert 0 < binding < 90  # binds mid-sweep, not at rest, not only at the end
    assert collisions[0]["colliding_union"] == ["base"]


# ---- 7.4 fixed set is all other unions ---------------------------------------


def test_fixed_set_is_all_other_unions(tmp_path):
    # arm orbits clear of `base`, but a third union `wall` sits in the arc.
    _box_stl(tmp_path / "base.stl", (10, 10, 10), (0, 0, 0))
    _box_stl(tmp_path / "arm.stl", (10, 10, 10), (20, 0, 0))
    _box_stl(tmp_path / "wall.stl", (10, 10, 10), (0, 14, 0))
    plan = _plan([_revolute_entry([0, 90])], part_ids=("base", "arm", "wall"))
    issues = run_kinematic_check(plan, str(tmp_path))
    collisions = [i for i in issues if i["type"] == "motion_collision"]
    assert len(collisions) == 1
    assert collisions[0]["colliding_union"] == ["wall"]


# ---- 7.3 print-in-place joint is swept, not skipped --------------------------


def test_print_in_place_two_unions_one_plate_is_swept(blocking_stls):
    # Two unions on one plate are still two STLs to the checker; nothing special.
    plan = {
        "parts": [
            {"id": "base", "plate": "shared"},
            {"id": "arm", "plate": "shared"},
        ],
        "kinematics": [_revolute_entry([0, 90])],
    }
    issues = run_kinematic_check(plan, str(blocking_stls))
    assert any(i["type"] == "motion_collision" for i in issues)


def test_pin_hinge_leaf_swept_against_other_leaf(tmp_path):
    # A print-in-place pin_hinge part declares its two leaf unions (leaf_a, leaf_b) on
    # one plate; the sweep runs leaf_a against leaf_b -- the hinge's own motion -- rather
    # than seeing them as one frozen blob.
    _box_stl(tmp_path / "leaf_a.stl", (10, 10, 10), (20, 0, 0))  # orbits the Z axis
    _box_stl(tmp_path / "leaf_b.stl", (10, 10, 10), (0, 14, 0))  # sits in leaf_a's arc
    plan = {
        "parts": [
            {
                "id": "hinge",
                "unions": [{"id": "leaf_a", "plate": "h"}, {"id": "leaf_b", "plate": "h"}],
            }
        ],
        "kinematics": [_revolute_entry([0, 90], moving="leaf_a")],
    }
    issues = run_kinematic_check(plan, str(tmp_path))
    collisions = [i for i in issues if i["type"] == "motion_collision"]
    assert len(collisions) == 1
    assert collisions[0]["colliding_union"] == ["leaf_b"]


# ---- sweep bounds and inclusivity --------------------------------------------


def test_sweep_does_not_exceed_required_range():
    values = [v for v, _ in iter_poses(_revolute_entry([0, 90], step=7))]
    assert max(values) <= 90 + 1e-9
    assert values[0] == 0 and values[-1] == 90  # closed endpoints included


def test_sweep_range_straddles_zero():
    values = [v for v, _ in iter_poses(_revolute_entry([-30, 90], step=10))]
    assert values[0] == -30 and values[-1] == 90
    assert any(abs(v) < 1e-9 for v in values)  # passes through zero


# ---- 7.5 bound inclusivity ---------------------------------------------------


def test_open_bounds_excluded():
    closed = _sweep_values(0, 90, 5)
    assert closed[0] == 0 and closed[-1] == 90
    open_lo = _sweep_values(0, 90, 5, lo_inc=False)
    assert 0 not in open_lo and open_lo[-1] == 90
    open_hi = _sweep_values(0, 90, 5, hi_inc=False)
    assert open_hi[0] == 0 and 90 not in open_hi


# ---- fcl missing degrades gracefully -----------------------------------------


def test_fcl_missing_skips_sweep_keeps_numeric_check(clear_stls, monkeypatch):
    monkeypatch.setitem(sys.modules, "fcl", None)  # `import fcl` -> ImportError
    plan = _plan([_revolute_entry([0, 270])])  # also exceeds limit
    issues = run_kinematic_check(plan, str(clear_stls))
    skipped = [i for i in issues if i["type"] == "check_skipped"]
    assert len(skipped) == 1
    assert skipped[0]["severity"] == "warning"
    assert any(i["type"] == "range_exceeds_limit" for i in issues)


# ---- 7.7 plan_validate cross-checks ------------------------------------------


def _write_plan(tmp_path, kinematics, extra_part=None):
    base_part = {
        "id": "base",
        "description": "base part",
        "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
        "interfaces": [],
        "blocks_needed": [],
    }
    arm_part = {
        "id": "arm",
        "description": "arm part",
        "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
        "interfaces": [],
        "blocks_needed": [],
    }
    if extra_part:
        arm_part.update(extra_part)
    plan = {
        "schema_version": 1,
        "intent": "kinematic validation fixture",
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "parts": [base_part, arm_part],
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


def test_plan_validate_rejects_unknown_moving_union(tmp_path):
    plan_path = _write_plan(tmp_path, [_revolute_entry([0, 90], moving="ghost")])
    errors = validate_plan(plan_path)
    assert any("moving_union 'ghost' is not a union id" in e for e in errors)


def test_plan_validate_rejects_invalid_placement_axis(tmp_path):
    bad = {"placement": {"rotate": [{"axis": "Q", "angle_deg": 10}]}}
    plan_path = _write_plan(tmp_path, [_revolute_entry([0, 90])], extra_part=bad)
    errors = validate_plan(plan_path)
    assert any("placement" in e.lower() or "axis" in e.lower() for e in errors)


def test_plan_validate_accepts_valid_placement_and_plate(tmp_path):
    good = {
        "plate": "shared",
        "placement": {
            "rotate": [{"axis": "X", "angle_deg": 90}],
            "translate_mm": [0, 0, 5],
        },
    }
    plan_path = _write_plan(tmp_path, [_revolute_entry([0, 90])], extra_part=good)
    errors = validate_plan(plan_path)
    assert errors == []


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


def test_plan_validate_rejects_unit_field(tmp_path):
    # `unit` was removed from the kinematics entry (derived from `type`); the schema rejects it.
    entry = _revolute_entry([0, 90])
    entry["unit"] = "deg"
    plan_path = _write_plan(tmp_path, [entry])
    errors = validate_plan(plan_path)
    assert any("unit" in e.lower() for e in errors)
