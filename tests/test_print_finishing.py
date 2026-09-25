"""Print-pose finishing: print_up(), pose-aware teardrops, env plumbing, export, provenance."""

import json
import math
import os

import cadquery as cq
import pytest
from conftest import minimal_plan
from conftest import run_wrapper as run

from blocks import print_up, teardrop_bore, teardrop_post
from exporters import _load_result
from freshness import pose_stale_ids, read_manifest
from model_export import export_model

FLIP_X = [{"axis": "X", "angle_deg": 180}]
TILT_Y = [{"axis": "Y", "angle_deg": 90}]


def _bb(wp):
    return wp.val().BoundingBox()


def test_print_up_unset_is_plus_z(monkeypatch):
    monkeypatch.delenv("CQ_PRINT_ROTATE", raising=False)
    assert print_up() == (0.0, 0.0, 1.0)


def test_print_up_flipped_x(monkeypatch):
    monkeypatch.setenv("CQ_PRINT_ROTATE", json.dumps(FLIP_X))
    assert print_up()[2] == pytest.approx(-1.0)


def test_print_up_sideways(monkeypatch):
    # Y+90 sends authored +X to build -Z, so build +Z is authored -X
    monkeypatch.setenv("CQ_PRINT_ROTATE", json.dumps(TILT_Y))
    assert print_up() == pytest.approx((-1.0, 0.0, 0.0), abs=1e-9)


def test_teardrop_bore_print_up_flipped_puts_apex_down():
    bb = _bb(teardrop_bore(d=8.0, depth=4.0, print_up=(0, 0, -1)))
    assert bb.zmin == pytest.approx(-4.0, abs=1e-3)  # apex at -Z
    assert bb.zmax == pytest.approx(4.0, abs=1e-3)


def test_teardrop_bore_print_up_sideways_puts_apex_on_x():
    bb = _bb(teardrop_bore(d=8.0, depth=4.0, print_up=(1, 0, 0)))
    assert bb.xmax == pytest.approx(4.0, abs=1e-3)  # apex toward +X


def test_teardrop_bore_print_up_along_axis_is_unrotated():
    a = _bb(teardrop_bore(d=8.0, depth=4.0, print_up=(0, 1, 0)))
    b = _bb(teardrop_bore(d=8.0, depth=4.0))
    assert a.zmax == pytest.approx(b.zmax) and a.zmin == pytest.approx(b.zmin)


def test_teardrop_post_print_up_flipped_moves_flat_to_top():
    up = _bb(teardrop_post(d=6.0, length=5.0, print_up=(0, 0, 1)))
    flipped = _bb(teardrop_post(d=6.0, length=5.0, print_up=(0, 0, -1)))
    # default: circular arc on top, flat bottom short of the full radius
    assert up.zmax == pytest.approx(3.0, abs=1e-3) and up.zmin > -3.0 + 1e-3
    assert flipped.zmin == pytest.approx(-3.0, abs=1e-3) and flipped.zmax < 3.0 - 1e-3
    assert math.isclose(up.zmax - up.zmin, flipped.zmax - flipped.zmin, abs_tol=1e-3)


_POSE_SCRIPT = """
import cadquery as cq
from blocks import print_up
h = 6 if print_up()[2] < 0 else 4
result = cq.Workplane('XY').box(20, 20, h)
"""


def test_load_result_sets_and_restores_env(tmp_path, monkeypatch):
    monkeypatch.delenv("CQ_PRINT_ROTATE", raising=False)
    script = tmp_path / "p.py"
    script.write_text(_POSE_SCRIPT)
    assert _bb(_load_result(str(script))).zlen == pytest.approx(4)
    assert _bb(_load_result(str(script), FLIP_X)).zlen == pytest.approx(6)
    assert "CQ_PRINT_ROTATE" not in os.environ


def test_runner_print_rotate_reaches_script(tmp_path):
    script = tmp_path / "p.py"
    script.write_text(_POSE_SCRIPT)
    pose = tmp_path / "o.json"
    pose.write_text(json.dumps({"rotate": FLIP_X}))
    _, plain = run(script)
    _, posed = run(script, "--print-rotate", str(pose))
    assert plain["success"] and posed["success"]
    assert plain["geometry"]["bbox"]["z_mm"] == pytest.approx(4)
    assert posed["geometry"]["bbox"]["z_mm"] == pytest.approx(6)


def test_export_runs_finishing_pass_and_stamps_pose(tmp_path):
    parts = tmp_path / "parts"
    parts.mkdir()
    (parts / "slab.py").write_text(_POSE_SCRIPT)
    plan = minimal_plan([{"id": "slab", "description": "slab"}])
    out = tmp_path / "out"
    posed = export_model(plan, str(parts), str(out), {"slab": {"rotate": FLIP_X}})
    manifest = read_manifest(str(out))
    assert manifest is not None
    assert manifest["unions"]["slab"]["print_rotate"] == FLIP_X
    import trimesh

    assert trimesh.load(posed["union_stls"]["slab"]).extents[2] == pytest.approx(6, abs=1e-3)
    assert isinstance(posed["pose_findings"], list)

    plain = export_model(plan, str(parts), str(tmp_path / "out2"))
    assert trimesh.load(plain["union_stls"]["slab"]).extents[2] == pytest.approx(4, abs=1e-3)
    manifest2 = read_manifest(str(tmp_path / "out2"))
    assert manifest2 is not None
    assert "print_rotate" not in manifest2["unions"]["slab"]


def test_pose_stale_ids():
    section = {"a": {"print_rotate": FLIP_X}, "b": {"print_rotate": FLIP_X}, "c": {}}
    stale = pose_stale_ids(section, {"a": FLIP_X, "b": TILT_Y, "c": TILT_Y, "d": FLIP_X})
    assert stale == {"b"}  # c has no recorded pose (unknown), d is absent from the manifest


def test_teardrop_bore_still_cuts_watertight_when_rotated():
    wall = cq.Workplane("XY").box(30, 10, 30)
    res = wall.cut(teardrop_bore(d=6.0, depth=10.0, print_up=(1, 0, 0)))
    assert res.findSolid().isValid()


def test_pose_stability_finding_reports_shift_and_keeps_none_when_stable():
    from print_finishing import orientation_for, pose_stability_finding

    plan = minimal_plan([{"id": "slab", "description": "slab"}])
    part = plan["parts"][0]
    slab = cq.Workplane("XY").box(40, 40, 3)
    best = orientation_for(slab, part, 45, "strength")["rotate"]
    stable = pose_stability_finding("slab", part, slab, best, plan)
    shifted = pose_stability_finding("slab", part, slab, [{"axis": "X", "angle_deg": 90}], plan)
    assert stable is None
    assert shifted is not None
    assert shifted["type"] == "pose_shift" and shifted["union"] == "slab"
