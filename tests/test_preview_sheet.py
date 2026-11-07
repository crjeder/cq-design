"""Feature views, marker and the 2 x 2 sheet (preview.py / render_preview.py --feature --sheet)."""

import os

import cadquery as cq
import numpy as np
from conftest import run_wrapper
from PIL import Image

import preview
import zbuffer
from feature_frame import feature_frame as _frame


def feature_frame(*args, **kwargs):
    found = _frame(*args, **kwargs)
    assert found is not None
    return dict(found)


HOLE_WALL = (
    "import cadquery as cq\n"
    "result = cq.Workplane('XY').box(60,40,3,centered=(True,True,False))"
    ".faces('>Z').workplane().center(10,5).hole(5)\n"
)


def hole_in_wall():
    wp = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    return wp.cut(cq.Workplane("XY").center(10, 5).circle(2.5).extrude(10))


def tile(color="white"):
    return Image.new("RGB", (50, 50), color)


def test_sheet_caps_at_four_tiles(tmp_path):
    tiles = [(tile(), f"t{i}") for i in range(6)]
    out = preview.render_sheet(tiles, str(tmp_path / "s.png"))
    four = preview.render_sheet(tiles[:4], str(tmp_path / "s4.png"), not_shown=["x"])
    assert Image.open(out).height == Image.open(four).height  # still 2 rows
    assert preview.sheet_legend(tiles) == ["t4 (not shown)", "t5 (not shown)"]


def test_sheet_legend_not_shown_and_not_located():
    legend = preview.sheet_legend([(tile(), "a")], ["usb_port"], ["lost"])
    assert legend == ["usb_port (not shown)", "lost (not located)"]


def test_marker_drawn_at_projected_anchor(tmp_path):
    wp = hole_in_wall()
    frame = feature_frame(wp.val(), (10, 5, 1.5), diameter_mm=5)
    anchor = (10, 5, 1.5)
    path = preview.render_feature_view(wp, str(tmp_path / "v.png"), frame, anchor)
    img = np.asarray(Image.open(path).convert("RGB"))
    center, size = preview._feature_focus(frame)
    verts, _ = preview._tessellate(wp)
    elev, azim = preview._NORMAL_CAMERA[tuple(frame["normal"])]
    project = zbuffer.make_camera(verts, elev, azim, img.shape[1], img.shape[0], (center, size))
    px, py, _ = project(anchor)
    assert img[int(py), int(px)].max() < 80  # leader line starts on the anchor
    yellow = (img[..., 0] > 240) & (img[..., 1] > 200) & (img[..., 2] < 40)
    assert yellow.any()  # badge


def test_feature_without_marker_has_no_badge(tmp_path):
    wp = hole_in_wall()
    path = preview.render_detail_view(wp, str(tmp_path / "d.png"), (10, 5, 1.5), 10, 90, -90)
    img = np.asarray(Image.open(path).convert("RGB"))
    assert not ((img[..., 0] > 240) & (img[..., 1] > 200) & (img[..., 2] < 40)).any()


def test_deep_feature_gets_section_flat_does_not(tmp_path):
    wp = hole_in_wall()
    frame = feature_frame(wp.val(), (10, 5, 1.5), diameter_mm=5)
    assert preview.feature_section_plane(frame) is not None
    out = preview.render_feature_section(wp, str(tmp_path / "s.png"), frame, (10, 5, 1.5))
    assert out is not None and os.path.exists(out)
    flat = {**frame, "depth_mm": 0.2}
    assert preview.feature_section_plane(flat) is None
    assert preview.render_feature_section(wp, str(tmp_path / "f.png"), flat, (10, 5, 1.5)) is None


def test_wrapper_sheet_with_features(tmp_path):
    script = tmp_path / "plate.py"
    script.write_text(HOLE_WALL)
    specs = [
        "name=bore;center=10,5,1.5;diameter=5",
        "name=ghost;center=500,500,500;diameter=3",
    ]
    args = ["--preview", "--preview-dir", str(tmp_path), "--sheet"]
    for spec in specs:
        args += ["--feature", spec]
    rc, data = run_wrapper(script, *args)
    assert rc == 0, data.get("stderr")
    names = [os.path.basename(p) for p in data["previews"]]
    assert names[1] == "plate_preview_sheet.png"  # sheet first among the extras
    assert "plate_preview_feature_bore.png" in names
    assert "plate_preview_feature_bore_section.png" in names
    assert not any("ghost" in n for n in names)  # not located -> no view


def test_wrapper_sheet_renders_at_most_four_features(tmp_path):
    script = tmp_path / "plate.py"
    script.write_text(HOLE_WALL)
    args = ["--preview", "--preview-dir", str(tmp_path), "--sheet"]
    for i in range(6):
        args += ["--feature", f"name=f{i};center=10,5,1.5;diameter=5"]
    rc, data = run_wrapper(script, *args)
    assert rc == 0, data.get("stderr")
    views = [p for p in data["previews"] if p.endswith(".png") and "_feature_f" in p]
    assert len({os.path.basename(p)[:-4].removesuffix("_section") for p in views}) == 4


def test_unlocated_feature_keeps_fallback_section(tmp_path):
    script = tmp_path / "plate.py"
    script.write_text(HOLE_WALL)
    args = ["--preview", "--preview-dir", str(tmp_path), "--cross-sections"]
    args += ["--feature", "name=ghost;center=500,500,500;diameter=3;section=x=10"]
    rc, data = run_wrapper(script, *args)
    assert rc == 0, data.get("stderr")
    names = [os.path.basename(p) for p in data["previews"]]
    assert "plate_preview_section_x_10mm.png" in names
