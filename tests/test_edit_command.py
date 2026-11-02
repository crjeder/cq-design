"""The /cq-design:edit call sequence: import a STEP, mesh input and edit, diff them."""

import cadquery as cq
from conftest import run_wrapper as run

from diff_models import diff_models

IMPORT = 'from blocks import import_solid\n\nresult = import_solid(r"{}")\n'


def _deliver(script, fmt, out_dir):
    rc, data = run(script, "--deliver", "--formats", fmt, "--output-dir", str(out_dir))
    assert rc == 0, data.get("errors")
    return data["stls"][0] if fmt == "stl" else None


def _setup(tmp_path, edit_body):
    step = tmp_path / "input.step"
    cq.exporters.export(cq.Workplane().box(40, 30, 10).translate((5, -7, 3)), str(step))
    build = tmp_path / "build"
    build.mkdir()
    inp = build / "edit_input.py"
    inp.write_text(IMPORT.format(step))
    edited = build / "input_edited.py"
    edited.write_text(IMPORT.format(step) + edit_body)
    return step, inp, edited


def test_noop_edit_diffs_identical(tmp_path):
    _, inp, edited = _setup(tmp_path, "")
    diff_dir = tmp_path / "build" / "edit_diff"
    r = diff_models(_deliver(inp, "stl", diff_dir), _deliver(edited, "stl", diff_dir))
    assert r["success"] and r["identical"]


def test_hole_edit_removes_material_and_keeps_frame(tmp_path):
    step, inp, edited = _setup(tmp_path, 'result = result.faces(">Z").workplane().hole(6)\n')
    diff_dir = tmp_path / "build" / "edit_diff"
    r = diff_models(_deliver(inp, "stl", diff_dir), _deliver(edited, "stl", diff_dir))
    assert r["success"] and not r["identical"]
    assert r["only_a_volume"] > 0 and r["only_b_volume"] == 0

    _deliver(edited, "step", tmp_path / "out")
    out = tmp_path / "out" / "input_edited.step"
    a = cq.importers.importStep(str(step)).findSolid().BoundingBox()
    b = cq.importers.importStep(str(out)).findSolid().BoundingBox()
    for k in ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax"):
        assert abs(getattr(a, k) - getattr(b, k)) < 1e-6
