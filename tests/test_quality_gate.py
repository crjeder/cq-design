"""Tests for quality_gate._analyze_stl overhang and geometry analysis."""

import json

import numpy as np
import pytest
import trimesh

import quality_gate

OVERHANG_DEG = 45.0


def _issues_of(issues, type_):
    return [i for i in issues if i["type"] == type_]


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
