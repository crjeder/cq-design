"""export_design_stl.py: STL + features file from a build script."""

import json
import os
import subprocess
import sys
from typing import cast

import trimesh
from conftest import REPO_ROOT

EXPORTER = os.path.join(REPO_ROOT, "src", "export_design_stl.py")

TWO_STAGE = """
import cadquery as cq
from cq_verify import verify_boolean, verify_stage
base = cq.Workplane("XY").box(40, 30, 10)
base = verify_stage(base, "base_shape", bbox=(-20, 20, -15, 15, -5, 5))
result = verify_boolean(base, base.cut(cq.Workplane("XY").box(6, 6, 20)), "cut", "hole")
"""


def _run(tmp_path, source):
    script = tmp_path / "part.py"
    script.write_text(source)
    out = tmp_path / "preview" / "design.stl"
    proc = subprocess.run(
        [sys.executable, EXPORTER, str(script), str(out)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.path.join(REPO_ROOT, "src")},
    )
    return proc.returncode, json.loads(proc.stdout), out


def test_export_writes_stl_and_features(tmp_path):
    rc, data, out = _run(tmp_path, TWO_STAGE)
    assert rc == 0 and data["success"] and data["errors"] == []
    assert len(cast(trimesh.Trimesh, trimesh.load(out)).faces) > 0
    features = json.loads(open(data["features"]).read())["features"]  # noqa: SIM115
    names = [f["name"] for f in features]
    assert names == ["base_shape", "hole"]


def test_missing_result_fails(tmp_path):
    rc, data, out = _run(tmp_path, "import cadquery as cq\nx = 1\n")
    assert rc == 1 and not data["success"]
    assert "result" in data["errors"][0]["message"]
    assert not out.exists()


def test_dict_result_is_one_compound(tmp_path):
    src = (
        "import cadquery as cq\n"
        "result = {'a': cq.Workplane('XY').box(10,10,10),"
        " 'b': cq.Workplane('XY').transformed(offset=(30,0,0)).box(10,10,10)}\n"
    )
    rc, data, out = _run(tmp_path, src)
    assert rc == 0
    assert trimesh.load(out).bounds[1][0] > 30
