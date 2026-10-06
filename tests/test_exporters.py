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


@pytest.mark.parametrize(
    "fmt,ext",
    [("stl", ".stl"), ("step", ".step"), ("3mf", ".3mf"), ("obj", ".obj"), ("iges", ".iges")],
)
def test_single_format_export(simple_box_script, tmp_path, fmt, ext):
    paths = run_exporters(str(simple_box_script), [fmt], str(tmp_path))
    assert len(paths) == 1
    assert paths[0].endswith(ext)
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


def _old_weld(verts, tris):
    remap: dict[tuple[float, float, float], int] = {}
    out: list[tuple[float, float, float]] = []
    old_to_new = [0] * len(verts)
    for i, v in enumerate(verts):
        key = (round(v.x, 6), round(v.y, 6), round(v.z, 6))
        idx = remap.get(key)
        if idx is None:
            idx = remap[key] = len(out)
            out.append((v.x, v.y, v.z))
        old_to_new[i] = idx
    return out, [(old_to_new[a], old_to_new[b], old_to_new[c]) for a, b, c in tris]


def test_weld_matches_dict_loop():
    import cadquery as cq

    from exporters.threemf_multi import _weld

    for shape in (
        cq.Workplane("XY").box(10, 10, 10),
        cq.Workplane("XY").cylinder(8, 5),
    ):
        verts, tris = shape.findSolid().tessellate(0.01, 0.1)
        new_v, new_t = _weld(verts, tris)
        old_v, old_t = _old_weld(verts, tris)
        assert new_v.tolist() == [list(v) for v in old_v]
        assert new_t.tolist() == [list(t) for t in old_t]


def test_writer_returns_nonmanifold_count(tmp_path):
    import cadquery as cq

    from exporters.threemf_multi import count_nonmanifold_edges, write_named_3mf

    shape = cq.Workplane("XY").box(20, 20, 6).faces(">Z").workplane().hole(8).val()
    path = str(tmp_path / "m.3mf")
    assert write_named_3mf([("a", "1", shape)], path) == 0
    assert count_nonmanifold_edges(path) == 0


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
