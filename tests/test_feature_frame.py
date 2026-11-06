import json
import os
import subprocess
import sys

import cadquery as cq
import pytest

from feature_frame import derive_frame, frames_for, parse_feature_spec

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def frame_of(*args):
    frame = derive_frame(*args)
    assert frame is not None
    return frame


def wall_with_hole():
    # 60x40x3 wall, z in [0, 3], 5 mm through bore at (10, 5)
    wp = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    return wp.cut(cq.Workplane("XY").center(10, 5).circle(2.5).extrude(10, both=True)).val()


def test_hole_in_wall():
    f = frame_of(wall_with_hole(), (10, 5, 1.5), 5)
    assert f["axis"] == "z" and f["depth_mm"] == pytest.approx(3)
    assert f["bbox_min"][:2] == pytest.approx([7.5, 2.5])
    assert f["bbox_max"][:2] == pytest.approx([12.5, 7.5])


def test_boss_on_plate():
    plate = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    boss = cq.Workplane("XY").workplane(offset=3).center(10, 5).circle(4).extrude(6)
    f = frame_of(plate.union(boss).val(), (10, 5, 6), 8)
    assert f["axis"] == "z" and f["sign"] == 1
    assert f["depth_mm"] == pytest.approx(6)  # boss height 6 (z 3..9)


def test_slot_normal_is_wall_normal_not_slot_side():
    wp = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    slot = cq.Workplane("XY").center(0, 0).slot2D(20, 3).extrude(10, both=True)
    f = frame_of(wp.cut(slot).val(), (0, 0, 1.5), 20)
    assert f["axis"] == "z" and f["depth_mm"] == pytest.approx(3)


def test_bottom_feature_sign_points_away_from_centre():
    f = frame_of(wall_with_hole(), (10, 5, 0), 5)
    assert f["sign"] == -1


def test_no_geometry_near_position():
    assert derive_frame(wall_with_hole(), (500, 500, 500), 5) is None


def test_frames_for_marks_unlocated():
    out = frames_for(
        wall_with_hole(),
        [
            {"name": "a", "center": (10, 5, 1.5), "extent": 5},
            {"name": "b", "center": (500, 0, 0), "extent": 5},
        ],
    )
    assert [o["located"] for o in out] == [True, False]
    assert "axis" not in out[1]


def test_parse_feature_spec():
    assert parse_feature_spec("name=a;center=1,2,3;size=4,6") == {
        "name": "a",
        "center": (1.0, 2.0, 3.0),
        "extent": 6.0,
    }
    assert parse_feature_spec("name=a;center=1,2,3")["extent"] == 0.0
    with pytest.raises(ValueError, match="center"):
        parse_feature_spec("name=a;diameter=3")


def test_cli(tmp_path):
    script = tmp_path / "m.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(60,40,3,centered=(True,True,False))"
        ".faces('>Z').workplane().center(10,5).hole(5)\n"
    )
    out = subprocess.run(
        [
            sys.executable,
            os.path.join(SRC, "feature_frame.py"),
            str(script),
            "--feature",
            "name=bore;center=10,5,1.5;diameter=5",
        ],
        capture_output=True,
        text=True,
        cwd=SRC,
    )
    assert out.returncode == 0, out.stderr
    (feat,) = json.loads(out.stdout)["features"]
    assert feat["located"] and feat["axis"] == "z" and feat["depth_mm"] == pytest.approx(3)
