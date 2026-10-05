"""Input-file failures give one actionable message, never a traceback. Fast, no CadQuery."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

SRC = Path(__file__).resolve().parent.parent / "src"


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(SRC / script), *args], capture_output=True, text=True, timeout=60
    )


@pytest.fixture
def bad_plans(tmp_path):
    truncated = tmp_path / "truncated.json"
    truncated.write_text('{"parts": [', encoding="utf-8")
    return {
        "missing": (str(tmp_path / "nope.json"), "not found"),
        "directory": (str(tmp_path), "is a directory"),
        "malformed": (str(truncated), "not valid JSON (line 1"),
    }


@pytest.mark.parametrize("kind", ["missing", "directory", "malformed"])
def test_plan_cli_message(bad_plans, tmp_path, kind):
    path, expected = bad_plans[kind]
    r = _run(
        "model_export.py", "--plan", path, "--parts-dir", str(tmp_path), "--out", str(tmp_path)
    )
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert r.stderr.startswith("error: BUILD_PLAN.json ")
    assert expected in r.stderr and path in r.stderr


def test_same_message_across_scripts(tmp_path):
    missing = str(tmp_path / "nope.json")
    a = _run("model_export.py", "--plan", missing, "--parts-dir", ".", "--out", ".")
    b = _run("toolpath_speed.py", "--plan", missing, "--script", "x.py")
    assert a.stderr == b.stderr


def test_plan_summary_missing(tmp_path):
    r = _run("plan.py", "summary", str(tmp_path / "nope.json"))
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "not found" in r.stderr


def test_quality_gate_file_error_issue(tmp_path):
    script = tmp_path / "p.py"
    script.write_text("result = None\n", encoding="utf-8")
    r = _run("quality_gate.py", "--script", str(script), "--plan", str(tmp_path / "nope.json"))
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["passed"] is False
    assert [i["type"] for i in out["issues"]] == ["file_error"]
    assert "Traceback" not in r.stderr


def test_wrapper_file_error_keeps_contract(tmp_path):
    script = tmp_path / "p.py"
    script.write_text(
        "import cadquery as cq\nresult = cq.Workplane().box(1, 1, 1)\n", encoding="utf-8"
    )
    r = _run("run_cadquery_model.py", str(script), "--print-rotate", str(tmp_path / "nope.json"))
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["success"] is False
    assert out["errors"][0]["type"] == "file_error"
    for key in (
        "geometry",
        "stl",
        "stls",
        "preview",
        "previews",
        "watertight",
        "stdout",
        "stderr",
        "returncode",
    ):
        assert key in out


def test_stl_missing_vs_invalid(tmp_path):
    from mesh_io import load_mesh as load_stl

    with pytest.raises(ValueError, match="STL not found"):
        load_stl(str(tmp_path / "nope.stl"))
    bad = tmp_path / "bad.stl"
    bad.write_text("garbage", encoding="utf-8")
    with pytest.raises(ValueError, match="not a valid STL|no "):
        load_stl(str(bad))
