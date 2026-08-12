"""Tests for the minimal-cutout bisection search tool.

Fixture geometry: `arm` is a box whose outer (radial) reach is `10 - CLEARANCE_MM`,
swept 0..90 deg about Z at the origin; `base` is a fixed box positioned so the
swept arm's outer edge only reaches it when CLEARANCE_MM is small (a shorter reach
avoids the wall). The ideal-geometry pass/fail boundary sits at CLEARANCE_MM=5
(worked out from the box extents), comfortably inside the [0, 9] test bounds --
tests assert the converged value lands near that neighborhood, not at the exact
theoretical edge (mesh tessellation and the sweep's penetration tolerance shift it
a little).
"""

import json
import os
import subprocess
import sys

import pytest

import minimal_cutout_search as mcs

ARM_SCRIPT = (
    "import cadquery as cq\n\n"
    "CLEARANCE_MM = 0.0  # notch depth removed from the outer (far) edge, mm\n"
    "_outer = 10.0 - CLEARANCE_MM\n"
    'result = cq.Workplane("XY").box(_outer, 10, 10, centered=(False, True, True))\n'
)

BASE_SCRIPT = 'import cadquery as cq\n\nresult = cq.Workplane("XY").box(10, 10, 10)\n'


def _plan():
    return {
        "parts": [
            {"id": "base", "placement": {"translate_mm": [0, 25, 0]}},
            {"id": "arm", "placement": {"translate_mm": [15, 0, 0]}},
        ],
        "kinematics": [
            {
                "joint_id": "arm_joint",
                "moving_union": "arm",
                "axis_origin_mm": [0, 0, 0],
                "axis_dir": "Z",
                "type": "revolute",
                "required_range": [0, 90],
                "step": 5,
                "mechanical_limit": [0, 180],
            }
        ],
    }


@pytest.fixture
def fixture_dir(tmp_path):
    (tmp_path / "arm.py").write_text(ARM_SCRIPT, encoding="utf-8")
    (tmp_path / "base.py").write_text(BASE_SCRIPT, encoding="utf-8")
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir()
    plan = _plan()
    mcs._export_part_stls(str(tmp_path / "base.py"), plan, "base", str(stl_dir))
    return tmp_path, plan, stl_dir


# ---- 1.3 parameter locate + rewrite round trip ---------------------------------


def test_read_and_set_parameter_value_round_trip(tmp_path):
    script = tmp_path / "p.py"
    script.write_text("X = 8.0\nCLEARANCE_MM = 2.0  # notch depth, mm\nY = 3\n", encoding="utf-8")
    assert mcs.read_parameter_value(str(script), "CLEARANCE_MM") == 2.0

    mcs.set_parameter_value(str(script), "CLEARANCE_MM", 5.25)

    assert mcs.read_parameter_value(str(script), "CLEARANCE_MM") == 5.25
    text = script.read_text(encoding="utf-8")
    assert "CLEARANCE_MM = 5.25  # notch depth, mm" in text
    assert "X = 8.0" in text and "Y = 3" in text  # other lines untouched


def test_unknown_parameter_raises(tmp_path):
    script = tmp_path / "p.py"
    script.write_text("X = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mcs.read_parameter_value(str(script), "MISSING")


# ---- 2.3 candidate evaluation ---------------------------------------------------


def test_candidate_evaluation_known_collide_and_clear(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    arm_script = str(tmp_path / "arm.py")
    collides = mcs.evaluate_candidate(
        arm_script, "arm", plan, str(stl_dir), "arm_joint", "CLEARANCE_MM", 0.0
    )
    clears = mcs.evaluate_candidate(
        arm_script, "arm", plan, str(stl_dir), "arm_joint", "CLEARANCE_MM", 9.0
    )
    assert collides is False
    assert clears is True


def test_only_searched_union_stl_is_rewritten(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    base_stl = stl_dir / "base.stl"
    before = base_stl.read_bytes()

    mcs.evaluate_candidate(
        str(tmp_path / "arm.py"), "arm", plan, str(stl_dir), "arm_joint", "CLEARANCE_MM", 9.0
    )

    assert base_stl.read_bytes() == before


# ---- 3.4 bounds precondition + bisection convergence ---------------------------


def test_search_converges_between_known_bounds(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    arm_script = str(tmp_path / "arm.py")

    converged = mcs.search(
        arm_script,
        "arm",
        plan,
        str(stl_dir),
        "arm_joint",
        "CLEARANCE_MM",
        0.0,
        9.0,
        tolerance_mm=0.1,
    )

    assert 3.0 < converged < 7.0  # boundary sits near CLEARANCE_MM=5 for this geometry
    # (mesh tessellation + the sweep's penetration tolerance shift the exact measured
    # boundary a bit off the ideal-geometry value; the bracket just checks it landed in
    # the expected neighborhood, not the theoretical edge)
    # search() must not have modified the original script
    assert mcs.read_parameter_value(arm_script, "CLEARANCE_MM") == 0.0


def test_search_rejects_lo_that_already_clears(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    with pytest.raises(mcs.BoundsError, match="--lo"):
        mcs.search(
            str(tmp_path / "arm.py"),
            "arm",
            plan,
            str(stl_dir),
            "arm_joint",
            "CLEARANCE_MM",
            9.0,
            9.5,
        )


def test_search_rejects_hi_that_still_collides(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    with pytest.raises(mcs.BoundsError, match="--hi"):
        mcs.search(
            str(tmp_path / "arm.py"),
            "arm",
            plan,
            str(stl_dir),
            "arm_joint",
            "CLEARANCE_MM",
            0.0,
            0.5,
        )


# ---- 4.3 CLI end-to-end ----------------------------------------------------------

_SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
_SCRIPT_PATH = os.path.join(_SRC_DIR, "minimal_cutout_search.py")


def _run_cli(args):
    env = dict(os.environ, PYTHONPATH=_SRC_DIR)
    return subprocess.run(
        [sys.executable, _SCRIPT_PATH, *args], capture_output=True, text=True, env=env
    )


def test_cli_default_leaves_script_unmodified(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    arm_script = tmp_path / "arm.py"
    before = arm_script.read_text(encoding="utf-8")

    proc = _run_cli(
        [
            str(arm_script),
            "--param",
            "CLEARANCE_MM",
            "--plan",
            str(plan_path),
            "--part",
            "arm",
            "--joint-id",
            "arm_joint",
            "--stl-dir",
            str(stl_dir),
            "--lo",
            "0",
            "--hi",
            "9",
        ]
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert 3.0 < result["converged"] < 7.0
    assert result["recommended"] == pytest.approx(result["converged"] + 0.2)
    assert result["applied"] is False
    assert arm_script.read_text(encoding="utf-8") == before


def test_cli_apply_writes_recommended_value(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    arm_script = tmp_path / "arm.py"

    proc = _run_cli(
        [
            str(arm_script),
            "--param",
            "CLEARANCE_MM",
            "--plan",
            str(plan_path),
            "--part",
            "arm",
            "--joint-id",
            "arm_joint",
            "--stl-dir",
            str(stl_dir),
            "--lo",
            "0",
            "--hi",
            "9",
            "--apply",
        ]
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["applied"] is True
    assert mcs.read_parameter_value(str(arm_script), "CLEARANCE_MM") == pytest.approx(
        result["recommended"]
    )


def test_cli_reports_bounds_error(fixture_dir):
    tmp_path, plan, stl_dir = fixture_dir
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    proc = _run_cli(
        [
            str(tmp_path / "arm.py"),
            "--param",
            "CLEARANCE_MM",
            "--plan",
            str(plan_path),
            "--part",
            "arm",
            "--joint-id",
            "arm_joint",
            "--stl-dir",
            str(stl_dir),
            "--lo",
            "9",
            "--hi",
            "9.5",
        ]
    )

    assert proc.returncode == 1
    assert "error" in json.loads(proc.stdout)
