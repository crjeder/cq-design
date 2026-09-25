"""Tests for src/export_standalone.py (minimal per-part deliverable)."""

import subprocess
import sys

from export_standalone import export

CQ_ONLY = "import cadquery as cq\nresult = cq.Workplane('XY').box(1, 2, 3)\n"


def _run(tmp_path, bodies, parameters=False):
    parts = tmp_path / "build"
    parts.mkdir()
    for pid, body in bodies.items():
        (parts / f"{pid}.py").write_text(body, encoding="utf-8")
    (parts / "build.py").write_text("import mesh_io\n", encoding="utf-8")
    params = tmp_path / "parameters.py"
    if parameters:
        params.write_text("X = 1\n", encoding="utf-8")
    out = tmp_path / "standalone"
    ids = export(parts, out, params)
    return out, ids


def test_cadquery_only_ships_alone(tmp_path):
    out, ids = _run(tmp_path, {"a": CQ_ONLY})
    assert ids == ["a"]
    assert {p.name for p in out.iterdir()} == {"a.py", "pyproject.toml", "README.md"}
    toml = (out / "pyproject.toml").read_text()
    assert "cadquery" in toml and "cq-warehouse" not in toml and "trimesh" not in toml


def test_helpers_copied_and_tooling_not(tmp_path):
    body = "from cq_verify import verify_boolean\nfrom blocks import fillet_box\n" + CQ_ONLY
    out, _ = _run(tmp_path, {"a": body}, parameters=True)
    assert (out / "cq_verify.py").exists() and (out / "blocks" / "__init__.py").exists()
    assert (out / "parameters.py").exists()
    assert not (out / "mesh_io.py").exists() and not (out / "exporters").exists()
    assert not (out / "build.py").exists()


def test_heat_set_boss_adds_warehouse(tmp_path):
    out, _ = _run(tmp_path, {"a": "from blocks import heat_set_boss\n" + CQ_ONLY})
    assert "cq-warehouse" in (out / "pyproject.toml").read_text()


def test_unknown_import_listed_and_rerun_overwrites(tmp_path):
    out, _ = _run(tmp_path, {"a": "import numpy\n" + CQ_ONLY})
    assert "numpy" in (out / "README.md").read_text()
    (tmp_path / "build" / "a.py").write_text(CQ_ONLY, encoding="utf-8")
    export(tmp_path / "build", out)
    assert "numpy" not in (out / "README.md").read_text()


def test_shipped_script_runs_in_place(tmp_path):
    out, _ = _run(tmp_path, {"a": "from cq_verify import verify_boolean\n" + CQ_ONLY})
    r = subprocess.run([sys.executable, "a.py"], cwd=out, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
