import json
import os
import subprocess
import sys

import cadquery as cq

from section_select import detect_features, score_slices, select_sections

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


def u_channel():
    prof = [(-20, 0), (20, 0), (20, 20), (17, 20), (17, 3), (-17, 3), (-17, 20), (-20, 20)]
    wp = cq.Workplane("YZ").polyline(prof).close().extrude(30, both=True)
    for x in (-15, 15):  # notches in both walls
        wp = wp.cut(
            cq.Workplane("XY").box(6, 50, 8, centered=(True, True, False)).translate((x, 0, 12))
        )
    return wp.val()


def hollow_enclosure():
    wp = cq.Workplane("XY").box(40, 30, 20, centered=(True, True, False))
    wp = wp.cut(
        cq.Workplane("XY").box(36, 26, 20, centered=(True, True, False)).translate((0, 0, 2))
    )
    for x, y in ((-12, -8), (12, -8), (-12, 8), (12, 8)):
        wp = wp.union(cq.Workplane("XY").center(x, y).circle(2).extrude(15))
    return wp.val()


def test_slices_u_profile_cuts_across_channel():
    (first, *_) = score_slices(u_channel())
    assert first["axis"] == "x"


def test_slices_enclosure_mid_height_shows_posts():
    (first, *_) = score_slices(hollow_enclosure())
    assert first["axis"] == "z" and 2 < first["position_mm"] < 15


def test_slices_plain_box_and_reserved():
    assert score_slices(cq.Workplane("XY").box(10, 10, 10).val()) == []
    cuts = score_slices(hollow_enclosure())
    assert (
        score_slices(hollow_enclosure(), reserved=[(c["axis"], c["position_mm"]) for c in cuts])[0]
        != cuts[0]
    )


def test_slices_time_cap_returns_without_error():
    assert score_slices(hollow_enclosure(), time_cap_s=0) == []
