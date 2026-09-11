"""Tests for quality_gate._analyze_stl overhang and geometry analysis."""

import json

import numpy as np
import pytest
import trimesh

import quality_gate

OVERHANG_DEG = 45.0


def _issues_of(issues, type_):
    return [i for i in issues if i["type"] == type_]


def test_telemetry_stage_silent_on_base_plus_followup_pair(tmp_path):
    log = tmp_path / "attempts.jsonl"
    base = {
        "part_id": "lid",
        "attempt": 1,
        "outcome": "pass",
        "error_types": [],
        "visual_review": None,
        "prompt_chars": 1000,
        "model": "inline",
    }
    followup = {**base, "outcome": "fail", "error_types": ["visual_mismatch"]}
    log.write_text(json.dumps(base) + "\n" + json.dumps(followup) + "\n", encoding="utf-8")

    issues = quality_gate._run_telemetry_stage(str(log))

    assert issues == []


def test_telemetry_stage_warns_when_log_absent(tmp_path):
    issues = quality_gate._run_telemetry_stage(str(tmp_path / "attempts.jsonl"))

    assert _issues_of(issues, "telemetry_missing")


@pytest.fixture
def flat_bottom_cube_stl(tmp_path):
    """Watertight cube: its flat bottom face rests on the bed (Z=min), so it is
    bed contact -- NOT an unsupported overhang, despite the -Z normal being 90 deg
    from horizontal. The cube has no other downward faces, so no overhang at all."""
    stl = tmp_path / "cube.stl"
    trimesh.creation.box(extents=(10, 10, 10)).export(str(stl))
    return str(stl)


@pytest.fixture
def self_supporting_stl(tmp_path):
    """Axis-aligned octahedron; every downward face overhangs only 35.26 deg."""
    v = (
        np.array(
            [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
            dtype=float,
        )
        * 10
    )
    f = np.array(
        [
            [4, 0, 2],
            [4, 2, 1],
            [4, 1, 3],
            [4, 3, 0],
            [5, 2, 0],
            [5, 1, 2],
            [5, 3, 1],
            [5, 0, 3],
        ]
    )
    stl = tmp_path / "octa.stl"
    trimesh.Trimesh(vertices=v, faces=f, process=False).export(str(stl))
    return str(stl)


@pytest.fixture
def multi_overhang_stl(tmp_path):
    """Two downward faces above the limit: a flat 90 deg face and a 60 deg face.

    The flat face (centroid ~[3.333, 3.333, 5]) is the steepest and must be the
    reported worst region.
    """
    verts = np.array(
        [
            # flat downward triangle (normal 0,0,-1 -> 90 deg)
            [0, 0, 5],
            [0, 10, 5],
            [10, 0, 5],
            # tilted downward triangle (normal 0.5,0,-0.866 -> 60 deg)
            [100, 0, 0],
            [100, 10, 0],
            [108.66, 0, 5],
        ],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    stl = tmp_path / "multi.stl"
    trimesh.Trimesh(vertices=verts, faces=faces, process=False).export(str(stl))
    return str(stl)


@pytest.fixture
def non_watertight_stl(tmp_path):
    """Single upward-facing triangle: not watertight, no overhang."""
    verts = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]], dtype=float)
    faces = np.array([[0, 1, 2]])
    stl = tmp_path / "open.stl"
    trimesh.Trimesh(vertices=verts, faces=faces, process=False).export(str(stl))
    return str(stl)


@pytest.fixture
def empty_stl(tmp_path):
    """ASCII STL with no facets."""
    stl = tmp_path / "empty.stl"
    stl.write_text("solid x\nendsolid x\n")
    return str(stl)


def test_flat_bottom_on_bed_not_flagged_as_overhang(flat_bottom_cube_stl):
    # Regression: a flat bottom face resting on the bed (Z=min) is supported by the
    # bed, not by support material, so it must NOT be reported as a 90 deg overhang.
    issues = quality_gate._analyze_stl(flat_bottom_cube_stl, OVERHANG_DEG)
    assert _issues_of(issues, "overhang_exceeded") == []


def test_self_supporting_emits_no_overhang(self_supporting_stl):
    issues = quality_gate._analyze_stl(self_supporting_stl, OVERHANG_DEG)
    assert _issues_of(issues, "overhang_exceeded") == []


def test_worst_region_tracks_steepest_face(multi_overhang_stl):
    issues = quality_gate._analyze_stl(multi_overhang_stl, OVERHANG_DEG)
    overhangs = _issues_of(issues, "overhang_exceeded")
    assert len(overhangs) == 1
    o = overhangs[0]
    assert o["worst_angle_deg"] == pytest.approx(90.0, abs=1e-3)
    assert o["location_xyz_mm"] == pytest.approx([3.333, 3.333, 5.0], abs=1e-2)


def test_authored_frame_overhang_cleared_by_print_orientation(multi_overhang_stl):
    # Regression (skill_gap_quality_gate_overhang_authored_frame): the STL is written
    # in the authored frame. Without the print rotation, the flat -Z face at z=5 reads
    # as a 90 deg overhang; rotating X+90 turns it into a vertical wall (0 deg), which
    # is what actually prints.
    without = _issues_of(
        quality_gate._analyze_stl(multi_overhang_stl, OVERHANG_DEG), "overhang_exceeded"
    )
    assert len(without) == 1 and without[0]["worst_angle_deg"] == pytest.approx(90.0, abs=1e-3)

    rotated = quality_gate._analyze_stl(
        multi_overhang_stl, OVERHANG_DEG, [{"axis": "X", "angle_deg": 90.0}]
    )
    assert _issues_of(rotated, "overhang_exceeded") == []


def test_run_gate_threads_orientation_rotate_into_overhang(
    monkeypatch, tmp_path, multi_overhang_stl
):
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text(json.dumps({"constraints": {"overhang_max_deg": OVERHANG_DEG}}))
    script = tmp_path / "part.py"
    script.write_text("result = None\n")
    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda *a, **k: ([], multi_overhang_stl, {})
    )
    monkeypatch.setattr(quality_gate, "_run_plan_validation_stage", lambda *a, **k: [])

    report = quality_gate.run_gate(
        str(script), str(plan), orientation={"rotate": [{"axis": "X", "angle_deg": 90.0}]}
    )
    assert _issues_of(report["issues"], "overhang_exceeded") == []


def test_non_watertight_reports_error(non_watertight_stl):
    issues = quality_gate._analyze_stl(non_watertight_stl, OVERHANG_DEG)
    errors = _issues_of(issues, "non_watertight")
    assert len(errors) == 1
    assert errors[0]["severity"] == "error"


def test_empty_mesh_reports_invalid_geometry(empty_stl):
    issues = quality_gate._analyze_stl(empty_stl, OVERHANG_DEG)
    assert len(issues) == 1
    assert issues[0]["type"] == "invalid_geometry"
    assert issues[0]["severity"] == "error"


def test_trimesh_missing_degrades_to_warning(monkeypatch, tmp_path):
    monkeypatch.setitem(__import__("sys").modules, "trimesh", None)
    issues = quality_gate._analyze_stl(str(tmp_path / "anything.stl"), OVERHANG_DEG)
    assert len(issues) == 1
    assert issues[0]["type"] == "check_skipped"
    assert issues[0]["severity"] == "warning"


def test_typed_occ_error_classified_as_severity_error(monkeypatch):
    """A split-out OCC error type (e.g. command_not_done) is still blocking,
    same as the old undifferentiated occ_exception."""

    class _FakeResult:
        stdout = json.dumps(
            {
                "errors": [
                    {
                        "type": "command_not_done",
                        "occ_class": "BRep_API",
                        "message": "boolean op failed",
                        "hint": "ensure overlap",
                    }
                ]
            }
        )
        stderr = ""

    monkeypatch.setattr(quality_gate.subprocess, "run", lambda *a, **k: _FakeResult())
    issues, _, _ = quality_gate._run_wrapper_check("script.py", {})
    assert len(issues) == 1
    assert issues[0]["type"] == "command_not_done"
    assert issues[0]["severity"] == "error"


def test_fix_loop_model_missing_config_is_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert quality_gate._fix_loop_model() is None


def test_fix_loop_model_inline_is_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skill_config.json").write_text(json.dumps({"models": {"fix_loop": "inline"}}))
    assert quality_gate._fix_loop_model() is None


def test_fix_loop_model_null_models_is_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skill_config.json").write_text(json.dumps({"models": None}))
    assert quality_gate._fix_loop_model() is None


def test_fix_loop_model_configured(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skill_config.json").write_text(
        json.dumps({"models": {"fix_loop": "claude-sonnet-5"}})
    )
    assert quality_gate._fix_loop_model() == "claude-sonnet-5"


def test_call_claude_appends_model_flag_when_configured(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skill_config.json").write_text(
        json.dumps({"models": {"fix_loop": "claude-sonnet-5"}})
    )
    captured = {}

    class _Result:
        returncode = 0
        stdout = "```python\nresult = 1\n```"
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(quality_gate.subprocess, "run", _fake_run)
    quality_gate._call_claude("fix this")
    assert captured["cmd"] == ["claude", "-p", "fix this", "--model", "claude-sonnet-5"]


def test_call_claude_no_model_flag_when_inline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    captured = {}

    class _Result:
        returncode = 0
        stdout = "```python\nresult = 1\n```"
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(quality_gate.subprocess, "run", _fake_run)
    quality_gate._call_claude("fix this")
    assert captured["cmd"] == ["claude", "-p", "fix this"]


def test_default_run_gate_reports_without_fixing(monkeypatch, tmp_path):
    # Regression: allow_fix defaults to False, so an erroring script must be left
    # byte-identical and no fix round should run.
    script = tmp_path / "part.py"
    script_bytes = b"# original script\n"
    script.write_bytes(script_bytes)
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text(json.dumps({"constraints": {}}))

    error_issue = {
        "source": "wrapper",
        "severity": "error",
        "type": "non_watertight",
        "message": "not watertight",
        "hint": "fix it",
    }
    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda *a, **k: ([error_issue], None, None)
    )

    def _unexpected_call(*a, **k):
        raise AssertionError("_call_claude must not run when allow_fix is False")

    monkeypatch.setattr(quality_gate, "_call_claude", _unexpected_call)

    report = quality_gate.run_gate(str(script), str(plan))

    assert report["fix_rounds"] == 0
    assert report["passed"] is False
    assert script.read_bytes() == script_bytes


# ---- hinge-guard-lint stage ------------------------------------------------


def _revolute_plan(moving_union="cradle", part_id="cradle", unions=None, joint_type="revolute"):
    part = {
        "id": part_id,
        "description": "test part",
        "dimensions": {"w_mm": 10, "d_mm": 10, "h_mm": 10},
        "interfaces": [],
        "blocks_needed": [],
    }
    if unions:
        part["unions"] = unions
    return {
        "parts": [part],
        "kinematics": [
            {
                "joint_id": "j1",
                "moving_union": moving_union,
                "axis_origin_mm": [0, 0, 0],
                "axis_dir": "Y",
                "type": joint_type,
                "required_range": [0, 90],
                "step": 5,
            }
        ],
    }


def test_hinge_guard_flags_hand_rolled_script(tmp_path):
    plan = _revolute_plan()
    script = tmp_path / "cradle.py"
    script.write_text("result = a.union(b)\n")
    issues = quality_gate._run_hinge_guard_stage(plan, str(script))
    assert len(issues) == 1
    assert issues[0]["type"] == "hinge_guard_missing"
    assert issues[0]["severity"] == "warning"
    assert issues[0]["unions"] == ["cradle"]


def test_hinge_guard_silent_with_verify_seated(tmp_path):
    plan = _revolute_plan()
    script = tmp_path / "cradle.py"
    script.write_text(
        "result = a.union(b)\nknuckle = verify_seated(riser, knuckle, '-z', 'hinge_ear')\n"
    )
    assert quality_gate._run_hinge_guard_stage(plan, str(script)) == []


def test_hinge_guard_silent_with_pin_hinge_block(tmp_path):
    plan = _revolute_plan()
    script = tmp_path / "cradle.py"
    script.write_text(
        "result = a.union(b)\nleaves = pin_hinge(length=10, knuckles=3, leaf_w=5, leaf_t=2)\n"
    )
    assert quality_gate._run_hinge_guard_stage(plan, str(script)) == []


def test_hinge_guard_non_hinge_part_never_checked(tmp_path):
    plan = {
        "parts": [
            {
                "id": "body",
                "description": "x",
                "dimensions": {"w_mm": 1, "d_mm": 1, "h_mm": 1},
                "interfaces": [],
                "blocks_needed": [],
            }
        ]
    }
    script = tmp_path / "body.py"
    script.write_text("result = a.union(b)\n")
    assert quality_gate._run_hinge_guard_stage(plan, str(script)) == []


def test_hinge_guard_multi_union_checks_only_hinge_associated_union(tmp_path):
    plan = _revolute_plan(
        moving_union="leaf_a",
        unions=[{"id": "leaf_a"}, {"id": "leaf_b"}],
    )
    script = tmp_path / "cradle.py"
    script.write_text("result = {'leaf_a': a.union(b), 'leaf_b': c.union(d)}\n")
    issues = quality_gate._run_hinge_guard_stage(plan, str(script))
    assert len(issues) == 1
    assert issues[0]["unions"] == ["leaf_a"]


def test_hinge_guard_spherical_kinematics_not_covered(tmp_path):
    plan = _revolute_plan(joint_type="spherical")
    script = tmp_path / "cradle.py"
    script.write_text("result = a.union(b)\n")
    assert quality_gate._run_hinge_guard_stage(plan, str(script)) == []


def test_hinge_guard_flags_pin_hinge_joint_member(tmp_path):
    plan = {
        "parts": [
            {
                "id": "door",
                "description": "x",
                "dimensions": {"w_mm": 1, "d_mm": 1, "h_mm": 1},
                "interfaces": [],
                "blocks_needed": [],
            },
            {
                "id": "wall",
                "description": "y",
                "dimensions": {"w_mm": 1, "d_mm": 1, "h_mm": 1},
                "interfaces": [],
                "blocks_needed": [],
            },
        ],
        "joints": [
            {
                "joint_id": "hinge1",
                "block": "pin_hinge",
                "params": {},
                "members": [
                    {"member": "leaf_a", "part": "door"},
                    {"member": "leaf_b", "part": "wall"},
                ],
            }
        ],
    }
    script = tmp_path / "door.py"
    script.write_text("result = a.union(b)\n")
    issues = quality_gate._run_hinge_guard_stage(plan, str(script))
    assert len(issues) == 1
    assert issues[0]["unions"] == ["door"]
