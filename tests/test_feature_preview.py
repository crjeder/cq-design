import json
import os

import cadquery as cq
import numpy as np
import pytest
from PIL import Image

import preview
from feature_frame import derive_frame
from render_preview import MAX_FEATURES, _render_features

HOLES = [(-20, 10), (-10, 10), (0, 10), (10, 10), (20, 10)]


def frame_of(*args):
    frame = derive_frame(*args)
    assert frame is not None
    return frame


def holed_wall(*holes):
    wp = cq.Workplane("XY").box(60, 40, 3, centered=(True, True, False))
    for x, y in holes:
        wp = wp.cut(cq.Workplane("XY").center(x, y).circle(2).extrude(10, both=True))
    return wp


def specs(positions):
    return [
        {"name": n, "center": (x, y, 1.5), "extent": 4.0}
        for n, (x, y) in zip("abcde", positions, strict=False)
    ]


def test_sheet_caps_at_four_tiles(tmp_path):
    img = Image.new("RGB", (50, 50), "white")
    tiles = [(img, f"t{i}") for i in range(5)]
    with pytest.raises(ValueError, match="at most 4"):
        preview.render_sheet(tiles, str(tmp_path / "s.png"))
    out = preview.render_sheet(tiles[:4], str(tmp_path / "s.png"), notes=["x (not shown)"])
    assert Image.open(out).size[0] > 1000


def small_views(monkeypatch):
    from functools import partial

    for fn in ("render_feature_view", "render_feature_section"):
        monkeypatch.setattr(preview, fn, partial(getattr(preview, fn), view_size=200))


def test_fifth_feature_is_not_shown_and_missing_one_not_located(tmp_path, monkeypatch):
    small_views(monkeypatch)
    feats = specs(HOLES) + [{"name": "f", "center": (500, 0, 0), "extent": 4.0}]
    tiles, notes, paths, frames = _render_features(holed_wall(*HOLES), feats, str(tmp_path), "p")
    assert len(tiles) == MAX_FEATURES == 4
    assert notes == ["e (not shown)", "f (not located)"]
    assert set(frames) == {"a", "b", "c", "d"}
    assert all(os.path.exists(p) for p in paths)
    assert tiles[0][1].startswith("1 a - ")


def test_marker_drawn_at_projected_anchor(tmp_path):
    wp = holed_wall((0, 0))
    frame = frame_of(wp.val(), (0, 0, 1.5), 4)
    out, view = preview.render_feature_view(wp, str(tmp_path / "v.png"), frame, 1, view_size=400)
    assert view == "+z"
    img = np.asarray(Image.open(out).convert("RGB"))
    assert ((img[:, :, 0] > 240) & (img[:, :, 1] > 190) & (img[:, :, 2] < 40)).sum() > 50  # badge
    _, project, _, _ = preview._render_panel(
        wp, 90, -90, 400, 400, focus=(tuple(frame["center"]), preview._frame_window(frame))
    )
    assert project is not None
    x, y, _ = project(preview._frame_anchor(frame, frame["sign"]))
    assert img[int(round(y)), int(round(x))].sum() < 120  # leader line starts at the anchor


def test_bottom_pocket_is_viewed_from_below(tmp_path):
    body = cq.Workplane("XY").box(40, 40, 10, centered=(True, True, False))
    pocket = cq.Workplane("XY").circle(4).extrude(4)
    wp = body.cut(pocket)
    frame = frame_of(wp.val(), (0, 0, 0), 8)
    assert frame["sign"] == -1 and frame["depth_mm"] == pytest.approx(4)
    _, view = preview.render_feature_view(wp, str(tmp_path / "v.png"), frame, 1, view_size=300)
    assert view == "-z"


def test_flat_feature_gets_no_section(tmp_path):
    frame = {
        "bbox_min": [0, 0, 0],
        "bbox_max": [4, 4, 0.2],
        "center": [2, 2, 0.1],
        "axis": "z",
        "sign": 1,
        "depth_mm": 0.2,
    }
    wp = cq.Workplane("XY").box(10, 10, 5)
    assert preview.render_feature_section(wp, str(tmp_path / "s.png"), frame, 1) is None


def test_feature_section_cuts_through_the_axis(tmp_path):
    wp = holed_wall((0, 0))
    frame = frame_of(wp.val(), (0, 0, 1.5), 4)
    sec = preview.render_feature_section(wp, str(tmp_path / "s.png"), frame, 1, view_size=300)
    assert sec is not None and sec.cut is not None
    assert sec.cut[0] in "xy" and sec.cut[1] == pytest.approx(0)


def test_cli_writes_sheet_first_and_frames(tmp_path):
    import subprocess
    import sys

    src = os.path.join(os.path.dirname(__file__), "..", "src")
    script = tmp_path / "m.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(60,40,3,centered=(True,True,False))"
        ".faces('>Z').workplane().center(10,5).hole(5)\n"
    )
    out = tmp_path / "m_preview.png"
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(src, "render_preview.py"),
            "--script",
            str(script),
            "--output",
            str(out),
            "--feature",
            "name=bore;center=10,5,1.5;diameter=5",
            "--feature",
            "name=ghost;center=900,0,0;diameter=5",
            "--sheet",
        ],
        capture_output=True,
        text=True,
        cwd=src,
    )
    assert proc.returncode == 0, proc.stderr
    extra = json.loads(proc.stdout.strip().splitlines()[-1])["extra_previews"]
    assert os.path.basename(extra[0]) == "m_preview_sheet.png"
    assert (tmp_path / "m_preview_feature_bore.png").exists()
    assert json.loads((tmp_path / "m_preview_frames.json").read_text())["bore"]["axis"] == "z"
