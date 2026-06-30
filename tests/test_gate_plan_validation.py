"""Tests for the gate's up-front plan-validation stage.

`run_gate` validates BUILD_PLAN.json before the kinematic stage, which raw-indexes plan
fields and would otherwise crash on a malformed plan. A validation failure becomes a
structured `plan_invalid` error and the kinematic stage is skipped. The kinematic stage is
monkeypatched to a sentinel so these tests assert skip/run behavior without needing the
per-union assembled STLs (and stay fast by not exercising a real motion sweep).
"""

import json

import quality_gate


def _valid_plan():
    """A schema-valid plan with one valid revolute joint (arm about Z)."""
    return {
        "schema_version": 1,
        "intent": "gate plan-validation fixture",
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
        "kinematics": [
            {
                "joint_id": "j1",
                "moving_union": "arm",
                "block": "hinge_leaf",
                "axis_origin_mm": [0, 0, 0],
                "axis_dir": "Y",
                "type": "revolute",
                "required_range": [0, 90],
                "step": 5,
            }
        ],
        "constraints": {
            "wall_min_mm": 1.2,
            "overhang_max_deg": 45,
            "dimension_tolerance_mm": 0.3,
        },
    }


def _write(tmp_path, plan):
    path = tmp_path / "BUILD_PLAN.json"
    path.write_text(json.dumps(plan))
    return str(path)


def _plan_invalid(issues):
    return [i for i in issues if i["type"] == "plan_invalid"]


def _run(good_script, plan_path, monkeypatch, kinematic_marker):
    """Run the gate with the kinematic stage replaced by a call-recording sentinel."""
    monkeypatch.setattr(
        quality_gate,
        "_run_kinematic_stage",
        lambda *a, **k: kinematic_marker.append(True) or [],
    )
    return quality_gate.run_gate(
        str(good_script),
        plan_path,
        allow_fix=False,
        stl_dir=str(good_script.parent),
    )


# ---- 3.1 malformed axis_dir -> structured error, no traceback ----------------


def test_invalid_axis_dir_yields_plan_invalid(tmp_path, good_script, monkeypatch):
    plan = _valid_plan()
    plan["kinematics"][0]["axis_dir"] = "XY"  # outside the X/Y/Z enum
    called: list = []
    report = _run(good_script, _write(tmp_path, plan), monkeypatch, called)
    assert _plan_invalid(report["issues"])  # structured, not a raised KeyError
    assert report["passed"] is False
    assert called == []  # kinematic stage skipped


# ---- 3.2 missing required_range -> skipped sweep -----------------------------


def test_missing_required_range_skips_kinematic_stage(tmp_path, good_script, monkeypatch):
    plan = _valid_plan()
    del plan["kinematics"][0]["required_range"]
    called: list = []
    report = _run(good_script, _write(tmp_path, plan), monkeypatch, called)
    assert _plan_invalid(report["issues"])
    assert report["passed"] is False
    assert called == []  # the raw-index path was never reached


# ---- 3.3 one issue per validator error ---------------------------------------


def test_each_validator_error_maps_to_one_issue(tmp_path, good_script, monkeypatch):
    monkeypatch.setattr(quality_gate, "_run_kinematic_stage", lambda *a, **k: [])
    monkeypatch.setattr(
        "plan_validate.validate_plan",
        lambda *a, **k: ["err one", "err two", "err three"],
    )
    report = quality_gate.run_gate(
        str(good_script),
        _write(tmp_path, _valid_plan()),
        allow_fix=False,
        stl_dir=str(good_script.parent),
    )
    invalid = _plan_invalid(report["issues"])
    assert len(invalid) == 3
    assert {i["message"] for i in invalid} == {"err one", "err two", "err three"}
    assert all(i["source"] == "plan" and i["severity"] == "error" for i in invalid)


# ---- 3.4 valid plan -> kinematic stage runs, no plan_invalid -----------------


def test_valid_plan_runs_kinematic_stage(tmp_path, good_script, monkeypatch):
    called: list = []
    report = _run(good_script, _write(tmp_path, _valid_plan()), monkeypatch, called)
    assert _plan_invalid(report["issues"]) == []
    assert called == [True]  # stage was invoked


# ---- 3.5 no kinematics -> validates clean, gates normally --------------------


def test_plan_without_kinematics_validates_clean(tmp_path, good_script, monkeypatch):
    plan = _valid_plan()
    del plan["kinematics"]
    called: list = []
    report = _run(good_script, _write(tmp_path, plan), monkeypatch, called)
    assert _plan_invalid(report["issues"]) == []
    assert called == [True]  # kinematic stage still called (it no-ops internally)
