"""Tests for fin_placement and the quality_gate fin hint / sacrificial handling."""

import json
from pathlib import Path

import cadquery as cq
import pytest
import trimesh

import fin_placement
import quality_gate
from blocks.supports import BASE_TINES

OVERHANG_DEG = 45.0


def _export(wp, path):
    cq.exporters.export(wp, str(path))
    return str(path)


@pytest.fixture
def arm_stl(tmp_path):
    """Pillar with a 15 mm flat-ceiling arm at z 10-20 on +X: a one-sided overhang."""
    pillar = cq.Workplane("XY").box(10, 10, 20, centered=(True, True, False))
    arm = cq.Workplane("XY").box(15, 10, 4, centered=(False, True, False)).translate((5, 0, 16))
    return _export(pillar.union(arm), tmp_path / "arm.stl")


@pytest.fixture
def cube_stl(tmp_path):
    return _export(
        cq.Workplane("XY").box(10, 10, 10, centered=(True, True, False)), tmp_path / "c.stl"
    )


def test_min_fin_height_matches_block_minimum():
    assert pytest.approx(2 * 0.2 * (BASE_TINES + 1)) == fin_placement.MIN_FIN_HEIGHT_MM


def test_overhang_gets_one_fin_under_it(arm_stl):
    mesh = trimesh.load(arm_stl, force="mesh")
    fins = fin_placement.suggest_fins(mesh, OVERHANG_DEG)
    assert len(fins) == 1
    f = fins[0]
    assert f["anchor_xyz_mm"][0] > 5 and f["anchor_xyz_mm"][2] == pytest.approx(16.0, abs=0.1)
    assert f["height_mm"] == pytest.approx(16.0, abs=0.1)
    assert f["outward_xyz"][2] == 0.0


def test_self_supporting_part_has_no_fins(cube_stl):
    mesh = trimesh.load(cube_stl, force="mesh")
    assert fin_placement.suggest_fins(mesh, OVERHANG_DEG) == []


def test_cli_emits_contract_and_leaves_input_untouched(arm_stl, capsys):
    before = Path(arm_stl).read_bytes()
    rc = fin_placement.main([arm_stl, "--overhang-deg", "45"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["success"] is True and out["errors"] == [] and len(out["fins"]) == 1
    assert Path(arm_stl).read_bytes() == before


def test_cli_reports_unreadable_file(tmp_path, capsys):
    rc = fin_placement.main([str(tmp_path / "missing.stl")])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["success"] is False and out["errors"][0]["type"] == "file_error"


def test_to_build_pose_undoes_rotation(arm_stl):
    rot = [{"axis": "Z", "angle_deg": 90.0}]
    fins = fin_placement.suggest_fins(trimesh.load(arm_stl, force="mesh"), OVERHANG_DEG)
    fin_placement.to_build_pose(fins, rot)
    x, y, z = fins[0]["anchor_xyz_mm"]
    bx, by, bz = fins[0]["build_anchor_xyz_mm"]
    assert (bx, by, bz) == pytest.approx((y, -x, z), abs=1e-3)


def _gate(monkeypatch, tmp_path, stls, plan_data):
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text(json.dumps(plan_data))
    script = tmp_path / "part.py"
    script.write_text("result = None\n")
    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda *a, **k: ([], stls[0], {}, list(stls))
    )
    monkeypatch.setattr(quality_gate, "_run_plan_validation_stage", lambda *a, **k: [])
    return quality_gate.run_gate(str(script), str(plan))


def _types(report):
    return [i["type"] for i in report["issues"]]


def test_gate_emits_fin_hint_for_overhang(monkeypatch, tmp_path, arm_stl):
    report = _gate(monkeypatch, tmp_path, [arm_stl], {"constraints": {"overhang_max_deg": 45}})
    hint = next(i for i in report["issues"] if i["type"] == "fin_hint")
    assert hint["severity"] == "info" and len(hint["fins"]) == 1
    assert "overhang_exceeded" in _types(report)


def test_gate_fin_hint_opt_out(monkeypatch, tmp_path, arm_stl):
    plan = {"constraints": {"overhang_max_deg": 45, "fin_hints": False}}
    report = _gate(monkeypatch, tmp_path, [arm_stl], plan)
    assert "fin_hint" not in _types(report) and "overhang_exceeded" in _types(report)


def test_gate_skips_sacrificial_union_and_reports_designed_support(monkeypatch, tmp_path, arm_stl):
    fin = _export(
        cq.Workplane("XY").box(12, 0.8, 10, centered=(True, True, False)), tmp_path / "fins.stl"
    )
    body = _export(
        cq.Workplane("XY").box(10, 10, 10, centered=(True, True, False)), tmp_path / "part.stl"
    )
    plan = {
        "constraints": {"overhang_max_deg": 45, "wall_min_mm": 1.2},
        "parts": [{"id": "part", "unions": [{"id": "part"}, {"id": "fins", "sacrificial": True}]}],
    }
    report = _gate(monkeypatch, tmp_path, [body, fin], plan)
    ds = [i for i in report["issues"] if i["type"] == "designed_support"]
    assert len(ds) == 1 and ds[0]["fin_union_count"] == 1
    assert not [i for i in report["issues"] if i.get("union") == "fins"]
