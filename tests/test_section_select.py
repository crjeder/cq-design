import json
import os
import subprocess
import sys

import cadquery as cq

from section_select import detect_features, select_sections

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def box_with_holes(*holes):
    wp = cq.Workplane("XY").box(60, 40, 10)
    for x, y, d in holes:
        wp = wp.cut(cq.Workplane("XY").center(x, y).circle(d / 2).extrude(20, both=True))
    return wp.val()


def test_through_hole():
    (f,) = detect_features(box_with_holes((10, 5, 5)))
    assert f["axis"] == "z" and f["center"] == [10, 5] and f["radius_mm"] == 2.5


def test_fillet_ignored():
    shape = cq.Workplane("XY").box(20, 20, 10).edges("|Z").fillet(2).val()
    assert detect_features(shape) == []


def test_counterbore_merged():
    wp = cq.Workplane("XY").box(40, 40, 10).faces(">Z").workplane().cboreHole(4, 8, 3)
    (f,) = detect_features(wp.val())
    assert f["kind"] == "stepped"


def test_axes_and_shared_plane():
    secs = select_sections(box_with_holes((10, 5, 5), (10, -8, 4)))
    assert secs[0]["axis"] == "x" and secs[0]["position_mm"] == 10
    assert len(secs[0]["features"]) == 2


def test_cap():
    holes = [(-25 + 7 * i, -18 + 5 * i, 4) for i in range(8)]
    assert len(select_sections(box_with_holes(*holes), max_cuts=3)) == 3


def test_reserved_dedupe():
    assert select_sections(box_with_holes((10.2, 5, 5)), reserved=[("x", 10)]) == []


def test_plain_box_empty():
    assert select_sections(cq.Workplane("XY").box(10, 10, 10).val()) == []


def test_cli(tmp_path):
    script = tmp_path / "m.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(60,40,10).faces('>Z').workplane()"
        ".center(10,5).hole(5)\n"
    )
    out = subprocess.run(
        [sys.executable, os.path.join(SRC, "section_select.py"), str(script)],
        capture_output=True,
        text=True,
        cwd=SRC,
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["extra_section_args"] == ["x=10"]
