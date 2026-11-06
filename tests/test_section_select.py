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
    # U profile in the YZ plane, running along x, with two notches through both walls
    wp = cq.Workplane("XY").box(40, 30, 20)
    wp = wp.cut(cq.Workplane("XY").box(50, 24, 20).translate((0, 0, 13)))
    for x in (-10, 10):
        wp = wp.cut(cq.Workplane("XY").box(4, 40, 8).translate((x, 0, 16)))
    return wp.val()


def open_enclosure_with_posts():
    wp = cq.Workplane("XY").box(60, 40, 30, centered=(True, True, False))
    wp = wp.cut(
        cq.Workplane("XY").box(56, 36, 30, centered=(True, True, False)).translate((0, 0, 2))
    )
    for x, y in ((-20, -12), (20, -12), (-20, 12), (20, 12)):
        wp = wp.union(cq.Workplane("XY").workplane(offset=2).center(x, y).circle(3).extrude(20))
    return wp.val()


def test_slices_pick_the_u_profile_for_a_notched_channel():
    cuts = score_slices(u_channel())
    assert len(cuts) <= 2
    assert any(c["axis"] == "x" for c in cuts)  # a cut across the channel shows the U


def test_slices_pick_mid_height_for_an_enclosure_with_posts():
    cuts = score_slices(open_enclosure_with_posts())
    z = [c for c in cuts if c["axis"] == "z"]
    assert z and 2 < z[0]["position_mm"] < 22  # through the posts, not above them


def test_slices_ignore_a_plain_box():
    assert score_slices(cq.Workplane("XY").box(20, 20, 20).val()) == []


def test_slices_skip_reserved_positions():
    shape = open_enclosure_with_posts()
    z = next(c for c in score_slices(shape) if c["axis"] == "z")["position_mm"]
    again = score_slices(shape, reserved=[("z", z)])
    assert all(not (c["axis"] == "z" and abs(c["position_mm"] - z) < 0.5) for c in again)


def test_slices_time_budget_returns_empty():
    assert score_slices(u_channel(), budget_s=-1) == []
