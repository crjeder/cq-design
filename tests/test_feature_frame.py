import json
import os
import subprocess
import sys

import cadquery as cq

from feature_frame import feature_frame as _frame


def feature_frame(*args, **kwargs):
    found = _frame(*args, **kwargs)
    assert found is not None
    return dict(found)


SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def test_hole_in_wall():
    # 3 mm top wall (z 0..3), 5 mm bore at (10, 5)
    wp = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    wp = wp.cut(cq.Workplane("XY").center(10, 5).circle(2.5).extrude(10))
    f = feature_frame(wp.val(), (10, 5, 1.5), diameter_mm=5)
    assert f["axis"] == "z" and f["normal"] == [0, 0, 1]
    assert f["depth_mm"] == 3.0
    assert f["bbox"]["min"][:2] == [7.5, 2.5] and f["bbox"]["max"][:2] == [12.5, 7.5]


def test_boss_on_plate():
    plate = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    boss = cq.Workplane("XY").workplane(offset=3).center(5, 5).circle(4).extrude(6)
    f = feature_frame(plate.union(boss).val(), (5, 5, 6), diameter_mm=8)
    assert f["normal"] == [0, 0, 1]
    assert f["depth_mm"] == 6.0


def test_slot_long_axis_x_on_top_wall():
    wp = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    wp = wp.cut(cq.Workplane("XY").slot2D(20, 4, 0).extrude(10))
    f = feature_frame(wp.val(), (0, 0, 1.5), size_mm=[20, 4])
    assert f["normal"] == [0, 0, 1]  # host wall normal, not the long slot walls' y
    assert f["depth_mm"] == 3.0


def test_bottom_feature_flips_sign():
    wp = cq.Workplane("XY").box(60, 40, 10)
    wp = wp.cut(cq.Workplane("XY").workplane(offset=-5).circle(3).extrude(2))
    f = feature_frame(wp.val(), (0, 0, -4), diameter_mm=6)
    assert f["normal"] == [0, 0, -1]


def test_no_geometry_near_position():
    shape = cq.Workplane("XY").box(10, 10, 10).val()
    assert _frame(shape, (100, 100, 100), diameter_mm=4) is None


def test_cli(tmp_path):
    script = tmp_path / "m.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(60,40,3,centered=(True,True,False))"
        ".faces('>Z').workplane().center(10,5).hole(5)\n"
    )
    cmd = [sys.executable, os.path.join(SRC, "feature_frame.py"), str(script)]
    out = subprocess.run(
        [*cmd, "--center", "10,5,1.5", "--diameter", "5"], capture_output=True, text=True, cwd=SRC
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["normal"] == [0, 0, 1]
    far = subprocess.run([*cmd, "--center", "500,500,500"], capture_output=True, text=True, cwd=SRC)
    assert json.loads(far.stdout) == {"located": False}


def test_port_in_side_wall_ignores_larger_floor_face():
    body = cq.Workplane("XY").box(80, 50, 30, centered=(True, True, False))
    body = body.cut(
        cq.Workplane("XY").box(76, 46, 30, centered=(True, True, False)).translate((0, 0, 2))
    )
    body = body.cut(cq.Workplane("XY").box(12, 10, 6).translate((-40, 0, 14)))
    f = feature_frame(body.val(), (-40, 0, 14), size_mm=[12, 6])
    assert f["axis"] == "x" and f["normal"] == [-1, 0, 0]
    assert f["depth_mm"] == 2.0
