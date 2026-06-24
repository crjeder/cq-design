"""Integration tests for the modular exporter.

Each format is tested by running the exporter against a known-good model
script and checking the output file exists and is non-empty.
"""

import os
import sys

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from exporters import ExportError, run_exporters  # noqa: E402


@pytest.fixture
def simple_box_script(tmp_path):
    """Minimal CadQuery script with a top-level `result` variable."""
    script = tmp_path / "simple_box.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(20, 15, 10)\n"
        "# no export call — exporter imports result directly\n"
    )
    return script


@pytest.fixture
def script_without_result(tmp_path):
    script = tmp_path / "no_result.py"
    script.write_text("import cadquery as cq\nshape = cq.Workplane('XY').box(10, 10, 10)\n")
    return script


# ---- format tests ----


def test_stl_export(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["stl"], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(".stl")
    assert os.path.getsize(paths[0]) > 0


def test_step_export(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["step"], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(".step")
    assert os.path.getsize(paths[0]) > 0


def test_threemf_export(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["3mf"], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(".3mf")
    assert os.path.getsize(paths[0]) > 0


def test_threemf_export_is_manifold(tmp_path):
    """3MF must weld tessellation seams; a curved face exposes the worst case."""
    from exporters.threemf_multi import count_nonmanifold_edges

    script = tmp_path / "holed.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(20, 20, 6).faces('>Z').workplane()"
        ".hole(8)\n"
    )
    paths = run_exporters(str(script), ["3mf"], str(tmp_path))
    assert count_nonmanifold_edges(paths[0]) == 0


def test_obj_export(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["obj"], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(".obj")
    assert os.path.getsize(paths[0]) > 0


def test_iges_export(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["iges"], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(".iges")
    assert os.path.getsize(paths[0]) > 0


def test_scad_export(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["scad"], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(".scad")
    assert os.path.getsize(paths[0]) > 0
    # companion STL must also exist
    stl = paths[0].replace(".scad", ".stl")
    assert os.path.exists(stl)
    # scad file must contain a limitation comment and import statement
    with open(paths[0]) as f:
        content = f.read()
    assert "import(" in content
    assert "mesh-based" in content


def test_multiple_formats(simple_box_script, tmp_path):
    paths = run_exporters(str(simple_box_script), ["stl", "3mf", "step"], str(tmp_path))
    assert len(paths) == 3
    exts = {os.path.splitext(p)[1] for p in paths}
    assert exts == {".stl", ".3mf", ".step"}


# ---- error cases ----


def test_unknown_format_raises(simple_box_script, tmp_path):
    with pytest.raises(ExportError, match="Unknown export format"):
        run_exporters(str(simple_box_script), ["xyz"], str(tmp_path))


def test_missing_result_variable_raises(script_without_result, tmp_path):
    with pytest.raises(ExportError, match="result"):
        run_exporters(str(script_without_result), ["stl"], str(tmp_path))
