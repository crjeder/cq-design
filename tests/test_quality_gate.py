"""Tests for quality_gate._analyze_stl overhang and geometry analysis."""

import json
import math
from typing import Any

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
    # in the build pose. Without the print rotation, the flat -Z face at z=5 reads
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


def test_overhang_over_clearance_opening_downgrades_to_info(multi_overhang_stl):
    # Regression (hitstertower-oversupport): a wall opening the plan declares must
    # stay open (finger access, card exit) still spans material overhead that reads
    # as an unsupported overhang -- but it should be advisory, not a call to add
    # support/redesign, once the plan names it.
    zones = [{"center": (3.333, 3.333, 5.0), "radius_mm": 2.0, "name": "finger_access"}]
    issues = _issues_of(
        quality_gate._analyze_stl(multi_overhang_stl, OVERHANG_DEG, clearance_zones=zones),
        "overhang_exceeded",
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == "info"
    assert "finger_access" in issues[0]["message"]


def test_overhang_outside_clearance_opening_stays_warning(multi_overhang_stl):
    zones = [{"center": (100.0, 100.0, 100.0), "radius_mm": 2.0, "name": "unrelated"}]
    issues = _issues_of(
        quality_gate._analyze_stl(multi_overhang_stl, OVERHANG_DEG, clearance_zones=zones),
        "overhang_exceeded",
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == "warning"


def test_clearance_opening_zones_maps_position_through_placement_and_rotate():
    plan: dict = {}
    part = {
        "placement": {"translate_mm": [10.0, 0.0, 0.0]},
        "interfaces": [
            {
                "type": "clearance_opening",
                "name": "finger_access",
                "position_mm": [0, 0, 0],
                "size_mm": [10, 6],
            },
            {"type": "screw_mount", "position_mm": [1, 1, 1]},
        ],
    }
    zones = quality_gate._clearance_opening_zones(
        plan, part, rotate=[{"axis": "Z", "angle_deg": 90.0}]
    )
    assert len(zones) == 1
    assert zones[0]["name"] == "finger_access"
    # placement translate then Z+90 rotate: (10,0,0) -> (0,10,0)
    assert zones[0]["center"] == pytest.approx((0.0, 10.0, 0.0), abs=1e-6)
    assert zones[0]["radius_mm"] == pytest.approx(math.hypot(5, 3) + 1.0)


def test_run_gate_threads_orientation_rotate_into_overhang(
    monkeypatch, tmp_path, multi_overhang_stl
):
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text(json.dumps({"constraints": {"overhang_max_deg": OVERHANG_DEG}}))
    script = tmp_path / "part.py"
    script.write_text("result = None\n")
    monkeypatch.setattr(
        quality_gate,
        "_run_wrapper_check",
        lambda *a, **k: ([], multi_overhang_stl, {}, [multi_overhang_stl]),
    )
    monkeypatch.setattr(quality_gate, "_run_plan_validation_stage", lambda *a, **k: [])

    report = quality_gate.run_gate(
        str(script), str(plan), orientation={"rotate": [{"axis": "X", "angle_deg": 90.0}]}
    )
    assert _issues_of(report["issues"], "overhang_exceeded") == []


def _run_gate_with_geo_issues(monkeypatch, tmp_path, geo_issues, plan_data=None):
    """run_gate with `_analyze_stl` stubbed to return `geo_issues` verbatim, and every
    other plan-consuming stage neutralized -- isolates print_recipe.supports derivation
    from real mesh geometry and plan-schema validation."""
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text(json.dumps(plan_data or {"constraints": {"overhang_max_deg": OVERHANG_DEG}}))
    script = tmp_path / "part.py"
    script.write_text("result = None\n")
    stl = tmp_path / "part.stl"
    stl.write_text("solid x\nendsolid x\n")
    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda *a, **k: ([], str(stl), {}, [str(stl)])
    )
    monkeypatch.setattr(quality_gate, "_analyze_stl", lambda *a, **k: geo_issues)
    monkeypatch.setattr(quality_gate, "_run_plan_validation_stage", lambda *a, **k: [])
    return quality_gate.run_gate(str(script), str(plan))


def test_print_recipe_supports_true_when_overhang_exceeded(monkeypatch, tmp_path):
    # Regression (silica-tray-support-claim): print_recipe.supports used to be
    # hardcoded False regardless of any overhang_exceeded finding, so a delivered
    # recipe always claimed "no support needed" even with a flagged overhang.
    overhang_warning = [
        {
            "source": "geometry",
            "severity": "warning",
            "type": "overhang_exceeded",
            "message": "Worst overhang 90.0° exceeds limit 45.0° over 100.0 mm² of faces",
            "hint": "Add chamfers or redesign overhanging features.",
        }
    ]
    report = _run_gate_with_geo_issues(monkeypatch, tmp_path, overhang_warning)

    assert report["passed"] is True
    assert report["print_recipe"]["supports"] is True


def test_print_recipe_supports_false_when_self_supporting(monkeypatch, tmp_path):
    report = _run_gate_with_geo_issues(monkeypatch, tmp_path, [])

    assert report["passed"] is True
    assert report["print_recipe"]["supports"] is False


def test_print_recipe_supports_false_when_overhang_downgraded_to_info(monkeypatch, tmp_path):
    # An advisory (info-severity) overhang bounding a declared clearance_opening must
    # not itself claim the model needs support.
    overhang_info = [
        {
            "source": "geometry",
            "severity": "info",
            "type": "overhang_exceeded",
            "message": "over the declared clearance opening 'finger_access'",
            "hint": "see the part's load path instead of adding support here",
        }
    ]
    report = _run_gate_with_geo_issues(monkeypatch, tmp_path, overhang_info)

    assert report["passed"] is True
    assert report["print_recipe"]["supports"] is False


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
    issues, _, _, _ = quality_gate._run_wrapper_check("script.py", {})
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
    assert captured["cmd"] == [
        "claude",
        "-p",
        "fix this",
        "--tools",
        "",
        "--model",
        "claude-sonnet-5",
    ]


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
    assert captured["cmd"] == ["claude", "-p", "fix this", "--tools", ""]


# ---- finding action classification ----------------------------------------


def test_classify_action_error_defaults_to_fix():
    issue = {"type": "non_watertight", "severity": "error"}
    assert quality_gate._classify_action(issue) == "fix"


def test_classify_action_warning_defaults_to_warn_only():
    issue = {"type": "edge_treatment", "severity": "warning"}
    assert quality_gate._classify_action(issue) == "warn_only"


def test_classify_action_info_defaults_to_warn_only():
    issue = {"type": "overhang_exceeded", "severity": "info"}
    assert quality_gate._classify_action(issue) == "warn_only"


@pytest.mark.parametrize("severity", ["error", "warning"])
def test_classify_action_stale_artifact_always_re_export(severity):
    issue = {"type": "stale_artifact", "severity": severity}
    assert quality_gate._classify_action(issue) == "re_export"


@pytest.mark.parametrize(
    "type_", ["motion_collision", "range_exceeds_limit", "contact_limited_stop"]
)
@pytest.mark.parametrize("severity", ["error", "warning"])
def test_classify_action_ambiguous_remedy_types_always_ask_user(type_, severity):
    issue = {"type": type_, "severity": severity}
    assert quality_gate._classify_action(issue) == "ask_user"


def test_run_gate_sets_action_on_every_issue(monkeypatch, tmp_path):
    error_issue = {
        "source": "wrapper",
        "severity": "error",
        "type": "non_watertight",
        "message": "not watertight",
        "hint": "fix it",
    }
    report = _run_gate_with_geo_issues(monkeypatch, tmp_path, [error_issue])
    assert all("action" in i for i in report["issues"])
    assert next(i for i in report["issues"] if i["type"] == "non_watertight")["action"] == "fix"


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
        quality_gate, "_run_wrapper_check", lambda *a, **k: ([error_issue], None, None, [])
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


def test_bridge_only_part_emits_no_overhang_warning(tmp_path):
    from test_print_orientation import _bridge_slab  # type: ignore[attr-defined]  # noqa: PLC0415

    stl = tmp_path / "bridge.stl"
    _bridge_slab(6.0).export(str(stl))
    issues = quality_gate._analyze_stl(str(stl), OVERHANG_DEG)
    assert not _issues_of(issues, "overhang_exceeded")
    assert _issues_of(issues, "bridges_detected")[0]["severity"] == "info"


# ---- parameter-routing check ----------------------------------------------


def _routing_setup(tmp_path, targets=("cradle",), joints=None, drift=("plate",)):
    from freshness import script_hash

    for pid in ("cradle", "plate"):
        (tmp_path / f"{pid}.py").write_text(f"{pid.upper()} = 1\n")
    baseline = {p: script_hash(str(tmp_path / f"{p}.py")) for p in ("cradle", "plate")}
    for pid in drift:
        (tmp_path / f"{pid}.py").write_text(f"{pid.upper()} = 2\n")
    plan = {
        "request_log": [
            {"ts": "2026-09-01T10:00:00+00:00", "kind": "initial", "text": "cradle"},
            {
                "ts": "2026-09-01T11:00:00+00:00",
                "kind": "correction",
                "text": "raise the ear",
                "level": "parameter",
                "targets": list(targets),
                "script_baseline": baseline,
            },
        ]
    }
    if joints:
        plan["joints"] = joints
    return plan, str(tmp_path / "cradle.py")


def test_routing_flags_untargeted_sibling_drift(tmp_path):
    plan, script = _routing_setup(tmp_path)
    issues = quality_gate._run_parameter_routing_stage(plan, script)
    assert [(i["type"], i["severity"], i["part_id"]) for i in issues] == [
        ("routing_violation", "warning", "plate")
    ]
    assert "raise the ear" in issues[0]["message"]


def test_routing_ignores_targeted_part_drift(tmp_path):
    plan, script = _routing_setup(tmp_path, drift=("cradle",))
    assert quality_gate._run_parameter_routing_stage(plan, script) == []


def test_routing_ignores_part_prefixed_target(tmp_path):
    plan, script = _routing_setup(tmp_path, targets=("cradle.ear",), drift=("cradle",))
    assert quality_gate._run_parameter_routing_stage(plan, script) == []


def test_routing_ignores_joint_linked_sibling(tmp_path):
    joints = [{"members": [{"member": "a", "part": "cradle"}, {"member": "b", "part": "plate"}]}]
    plan, script = _routing_setup(tmp_path, joints=joints)
    assert quality_gate._run_parameter_routing_stage(plan, script) == []


def test_routing_no_baseline_is_silent(tmp_path):
    plan, script = _routing_setup(tmp_path)
    del plan["request_log"][-1]["script_baseline"]
    assert quality_gate._run_parameter_routing_stage(plan, script) == []


def test_routing_skips_baseline_part_with_no_script(tmp_path):
    plan, script = _routing_setup(tmp_path)
    (tmp_path / "plate.py").unlink()
    assert quality_gate._run_parameter_routing_stage(plan, script) == []


def test_routing_uses_newest_baseline_only(tmp_path):
    plan, script = _routing_setup(tmp_path)
    older = {**plan["request_log"][-1], "ts": "2026-09-01T10:30:00+00:00"}
    older["script_baseline"] = {"plate": "stale-hash"}
    plan["request_log"].insert(1, older)
    issues = quality_gate._run_parameter_routing_stage(plan, script)
    assert [i["part_id"] for i in issues] == ["plate"]


def test_overhang_hint_names_teardrop_bore(multi_overhang_stl):
    o = _issues_of(
        quality_gate._analyze_stl(multi_overhang_stl, OVERHANG_DEG), "overhang_exceeded"
    )[0]
    assert "teardrop_bore" in o["hint"]


@pytest.fixture
def fin_stl(tmp_path):
    """Two triangles hinged on a seam along +X, folded to a 2 deg interior dihedral."""
    c, s = math.cos(math.radians(2.0)), math.sin(math.radians(2.0))
    verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, c, s]], dtype=float)
    stl = tmp_path / "fin.stl"
    trimesh.Trimesh(vertices=verts, faces=[[0, 1, 2], [1, 0, 3]], process=False).export(str(stl))
    return str(stl)


def test_fin_reports_sliver_fin_warning(fin_stl):
    f = _issues_of(quality_gate._analyze_stl(fin_stl, OVERHANG_DEG), "sliver_fin")
    assert len(f) == 1
    assert f[0]["severity"] == "warning"
    assert f[0]["fold_count"] == 1
    assert f[0]["sharpest_interior_deg"] == pytest.approx(2.0, abs=1e-3)
    assert f[0]["locations_xyz_mm"][0] == pytest.approx([0.5, 0.0, 0.0], abs=1e-4)
    assert "end the fillet" in f[0]["hint"].lower() and ".fillet()" in f[0]["hint"]


def test_clean_part_has_no_sliver_fin(flat_bottom_cube_stl, self_supporting_stl):
    for stl in (flat_bottom_cube_stl, self_supporting_stl):
        assert _issues_of(quality_gate._analyze_stl(stl, OVERHANG_DEG), "sliver_fin") == []


def test_sliver_fin_location_is_in_build_frame(fin_stl):
    f = _issues_of(
        quality_gate._analyze_stl(fin_stl, OVERHANG_DEG, [{"axis": "Z", "angle_deg": 90.0}]),
        "sliver_fin",
    )
    assert f[0]["locations_xyz_mm"][0] == pytest.approx([0.0, 0.5, 0.0], abs=1e-4)


_RECIPE_PLAN: dict[str, Any] = {
    "nozzle_mm": 0.4,
    "material": "PLA",
    "printer": "Snapmaker U1",
    "constraints": {"wall_min_mm": 1.2, "overhang_max_deg": 45},
}


def test_recipe_defaults_top_bottom_layers_and_layer_height_without_profile(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text("{}", encoding="utf-8")

    recipe = quality_gate._emit_print_recipe(_RECIPE_PLAN, None, plan_path=str(plan_path))

    assert recipe["top_bottom_layers"] == 4
    assert recipe["layer_height_mm"] == 0.2  # nozzle_mm * 0.5, unchanged from before


def test_recipe_reads_top_bottom_layers_from_constraints(tmp_path):
    plan = {**_RECIPE_PLAN, "constraints": {**_RECIPE_PLAN["constraints"], "top_bottom_layers": 6}}
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text("{}", encoding="utf-8")

    recipe = quality_gate._emit_print_recipe(plan, None, plan_path=str(plan_path))

    assert recipe["top_bottom_layers"] == 6


def test_recipe_reads_layer_height_from_profile_motion_block(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text("{}", encoding="utf-8")
    (tmp_path / "profile.json").write_text(
        json.dumps({"motion": {"layer_height_mm": 0.16}}), encoding="utf-8"
    )

    recipe = quality_gate._emit_print_recipe(_RECIPE_PLAN, None, plan_path=str(plan_path))

    assert recipe["layer_height_mm"] == 0.16


def test_recipe_ignores_profile_when_plan_path_not_given():
    recipe = quality_gate._emit_print_recipe(_RECIPE_PLAN, None)

    assert recipe["top_bottom_layers"] == 4
    assert recipe["layer_height_mm"] == 0.2


def test_hooked_stages_share_one_script_execution(tmp_path):
    """Edge-treatment and feature-presence findings come from a single script run."""
    from edge_treatment_check import run_edge_treatment_check
    from feature_presence_check import run_feature_presence_check

    counter = tmp_path / "runs.txt"
    script = tmp_path / "body.py"
    script.write_text(
        "import cadquery as cq\n"
        f"open({str(counter)!r}, 'a').write('x')\n"
        "result = (cq.Workplane('XY').box(40, 30, 30).edges('|Z').chamfer(2)\n"
        "          .cut(cq.Workplane('XY').box(9, 4, 3).translate((10, 0, 15))))\n",
        encoding="utf-8",
    )
    plan = {
        "parts": [
            {
                "id": "body",
                "interfaces": [{"type": "port_cutout", "position_mm": [10, 0, 17]}],
            }
        ]
    }
    orientation: dict[str, Any] = {"rotate": []}

    edge, feature = quality_gate._run_hooked_stages(plan, str(script), orientation)
    assert counter.read_text() == "x"
    assert edge == run_edge_treatment_check(plan, str(script), {"body": orientation})
    assert feature == run_feature_presence_check(plan, str(script))
    assert [i["type"] for i in edge] == ["edge_treatment"]
    assert [i["type"] for i in feature] == ["feature_drift"]


def test_hooked_load_feeds_later_stages_from_cache(tmp_path):
    """Toolpath-speed and Gridfinity load the same (script, no rotate) key as the hooked stage."""
    from exporters import _load_result

    counter = tmp_path / "runs.txt"
    script = tmp_path / "body.py"
    script.write_text(
        "import cadquery as cq\n"
        f"open({str(counter)!r}, 'a').write('x')\n"
        "result = cq.Workplane('XY').box(20, 20, 10)\n",
        encoding="utf-8",
    )
    plan = {"parts": [{"id": "body"}]}
    quality_gate._run_hooked_stages(plan, str(script), {"rotate": []})
    _load_result(str(script))
    assert counter.read_text() == "x"
