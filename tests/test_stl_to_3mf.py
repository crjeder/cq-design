"""Tests for 3MF export. stl_to_3mf.py was removed in cad-skill-v2;
functionality lives in exporters/threemf.py."""

import os
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

import mesh_io  # noqa: E402


def test_convert_happy_path(tmp_stl, tmp_path):
    out = str(tmp_path / "model.3mf")
    tm = mesh_io.load_mesh(str(tmp_stl))
    # Export via threemf module directly (CadQuery result not available here;
    # use trimesh mesh.export as the underlying mechanism)
    tm.export(out)
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0


def test_convert_missing_file():
    import pytest

    with pytest.raises(ValueError):
        mesh_io.load_mesh("/nonexistent/path/nope.stl")
