import itertools
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import cadquery as cq
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "evals"))

import cadgenbench_run  # type: ignore[import-not-found]  # noqa: E402  # pyright: ignore[reportMissingImports]


def _extents(shape):
    bb = shape.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen), (bb.center.x, bb.center.y, bb.center.z)


def test_canonical_pose_orders_extents_and_centres():
    for dims in [(10, 30, 20), (5, 10, 40), (40, 5, 10)]:
        box = cq.Workplane().box(*dims).translate((7, -3, 11)).findSolid()
        posed = cadgenbench_run.canonical_pose(box)
        extents, center = _extents(posed)
        assert [round(e, 3) for e in extents] == sorted(dims, reverse=True)
        assert all(abs(c) < 1e-6 for c in center)


def test_single_step_posed_through_placement(tmp_path):
    for i, dims in enumerate([(10, 30, 20), (5, 10, 40), (40, 5, 10), (20, 40, 10)]):
        body = cq.Workplane().box(*dims).faces(">Z").workplane().hole(3).translate((7, -3, 11))
        src, out = tmp_path / f"in{i}.step", tmp_path / f"out{i}.step"
        body.findSolid().exportStep(str(src))
        cadgenbench_run.write_candidate([src], out)
        posed = cq.importers.importStep(str(out)).findSolid()
        extents, center = _extents(posed)
        assert [round(e, 3) for e in extents] == sorted(dims, reverse=True)
        assert all(abs(c) < 1e-6 for c in center)
        assert abs(posed.Volume() - body.findSolid().Volume()) < 1e-6


def test_canonical_matrix_is_a_rotation_for_every_axis_order():
    for extents in itertools.permutations((1.0, 2.0, 3.0)):
        m = np.array(cadgenbench_run.canonical_matrix((0, 0, 0), extents))[:3, :3]
        assert np.allclose(m @ m.T, np.eye(3))
        assert np.isclose(np.linalg.det(m), 1.0)


def test_build_prompt_edit_fixture_invokes_edit_command(tmp_path):
    (tmp_path / "edit_description.txt").write_text("Add a 5 mm hole.\n")
    prompt = cadgenbench_run.build_prompt(tmp_path)
    assert prompt.startswith("/cq-design:edit input.step Add a 5 mm hole.")
    assert "build/build.py" not in prompt


def test_build_prompt_generation_fixture(tmp_path):
    (tmp_path / "input.png").write_text("x")
    prompt = cadgenbench_run.build_prompt(tmp_path)
    assert "engineering drawing (input.png" in prompt
    assert "build/build.py --formats step" in prompt and "/cq-design:edit" not in prompt


def test_write_candidate_falls_back_to_unposed_when_pose_breaks_it(tmp_path, monkeypatch):
    srcs = []
    for i, x in enumerate((7, 17)):
        src = tmp_path / f"in{i}.step"
        cq.Workplane().box(10, 20, 30).translate((x, 0, 0)).findSolid().exportStep(str(src))
        srcs.append(src)
    out = tmp_path / "101" / "output.step"
    monkeypatch.setattr(cadgenbench_run, "step_is_valid", lambda p: False)
    cadgenbench_run.write_candidate(srcs, out)
    extents, center = _extents(cq.importers.importStep(str(out)).findSolid())
    assert [round(e, 3) for e in extents] == [20, 20, 30]
    assert round(center[0], 3) == 12


@pytest.mark.parametrize("kind", ["session", "weekly"])
def test_generate_stops_at_first_usage_limit(tmp_path, monkeypatch, kind):
    data = tmp_path / "data"
    for fid in ("101", "102"):
        (data / fid).mkdir(parents=True)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs["cwd"])
        out = {"is_error": True, "result": f"You've hit your {kind} limit · resets 1pm"}
        return subprocess.CompletedProcess(cmd, 1, stdout=json.dumps(out), stderr="")

    monkeypatch.setattr(cadgenbench_run.subprocess, "run", fake_run)
    cadgenbench_run.generate(tmp_path / "run", data, ["101", "102"], 10, False)
    assert len(calls) == 1


def test_package_keeps_every_fixture_folder_and_does_not_agree(tmp_path):
    run = tmp_path / "run"
    (run / "101").mkdir(parents=True)
    (run / "101" / "output.step").write_text("x")
    meta = {
        "submitter_name": "a",
        "submission_name": "b",
        "agent_url": None,
        "notes": None,
        "agree_to_publish": False,
    }
    zip_path = cadgenbench_run.package(run, ["101", "201"], meta)
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert {"meta.json", "101/", "101/output.step", "201/"} <= names
        assert json.loads(zf.read("meta.json"))["agree_to_publish"] is False


def test_generate_keeps_work_dir_but_prunes_venv(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "101").mkdir(parents=True)

    def fake_run(fixture_dir, work, timeout_s, plugin_dir=None, effort=None):
        (work / ".venv").mkdir(parents=True)
        (work / ".venv" / "x").write_text("v")
        (work / "BUILD_PLAN.json").write_text("{}")
        return False

    monkeypatch.setattr(cadgenbench_run, "run_fixture", fake_run)
    cadgenbench_run.generate(tmp_path / "run", data, ["101"], 1, False)
    work = tmp_path / "run" / "_work" / "101"
    assert (work / "BUILD_PLAN.json").is_file() and not (work / ".venv").exists()


def test_run_fixture_seeds_cad_intent_profile(tmp_path, monkeypatch):
    fixture = tmp_path / "fx"
    fixture.mkdir()
    (fixture / "description.yaml").write_text("x: 1")
    monkeypatch.setattr(
        cadgenbench_run.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, "{}", ""),
    )
    work = tmp_path / "work"
    cadgenbench_run.run_fixture(fixture, work, 1)
    profile = json.loads((work / "profile.json").read_text(encoding="utf-8"))
    assert profile["design_intent"] == "cad"
    assert "clearance" not in cadgenbench_run.FIDELITY


def test_run_fixture_passes_effort_only_when_set(tmp_path, monkeypatch):
    fixture = tmp_path / "fx"
    fixture.mkdir()
    cmds = []

    def fake_run(cmd, **kwargs):
        cmds.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "{}", "")

    monkeypatch.setattr(cadgenbench_run.subprocess, "run", fake_run)
    cadgenbench_run.run_fixture(fixture, tmp_path / "a", 1)
    cadgenbench_run.run_fixture(fixture, tmp_path / "b", 1, effort="medium")
    assert "--effort" not in cmds[0]
    i = cmds[1].index("--effort")
    assert cmds[1][i + 1] == "medium"


def test_build_prompt_generation_uses_design_command(tmp_path):
    (tmp_path / "input.png").write_text("x")
    prompt = cadgenbench_run.build_prompt(tmp_path)
    assert prompt.startswith("/cq-design:design ")
    assert "input.png" in prompt and cadgenbench_run.FIDELITY in prompt


def _work(tmp_path, journal=(), plan=None, reports=None):
    (tmp_path / "build").mkdir(parents=True, exist_ok=True)
    (tmp_path / "build" / "journal.md").write_text("".join(f"- {ln}\n" for ln in journal))
    if plan is not None:
        (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan))
    for name, passed in (reports or {}).items():
        (tmp_path / "build" / name).write_text(json.dumps({"passed": passed}))
    return tmp_path


def test_audit_pipeline_plan_less_run(tmp_path):
    work = _work(tmp_path)
    (work / "build" / "plate.py").write_text("result = 1\n")
    audit = cadgenbench_run.audit_pipeline(work)
    assert audit == {
        "plan": False,
        "gate_result": False,
        "gate_passed": False,
        "b1_checked": False,
    }


def test_audit_pipeline_full_run_ignores_round_copy(tmp_path):
    plan = {"design_intent": "cad", "parts": [{"id": "block", "interfaces": []}]}
    journal = [
        "phase1/dimensions_approved: ok",
        "phase2/plan_written: ok",
        "phase2/plan_approved: ok b1=block:0",
        "phase3/part_accepted:block: ok",
        "phase3/design_approved: ok",
        "phase3/orientation_chosen: ok",
        "phase3/assembly_written: ok",
        "phase3/gate_result: pass, 0 remaining findings",
    ]
    reports = {"block.quality_gate.json": True, "block.quality_gate.round1.json": False}
    work = _work(tmp_path, journal, plan, reports)
    (work / "build" / "block.py").write_text("result = 1\n")
    assert all(cadgenbench_run.audit_pipeline(work).values())
