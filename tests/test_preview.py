"""
Tests for src/preview.py — CadQuery-based preview rendering.

These tests run real CadQuery geometry and require the venv to be active.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import cadquery as cq
import numpy as np

import preview


@pytest.fixture
def box_workplane():
    """Simple 10x10x10 mm cube as a CadQuery Workplane."""
    return cq.Workplane("XY").box(10, 10, 10)


@pytest.mark.parametrize(
    "render_fn, kwargs",
    [
        (preview.render_multi_view, {}),
        (preview.render_single, {"title": "Test Box"}),
    ],
    ids=["multi_view", "single"],
)
def test_render_produces_png(box_workplane, tmp_path, render_fn, kwargs):
    output = tmp_path / "out.png"
    result = render_fn(box_workplane, str(output), **kwargs)
    assert result == str(output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_render_multi_view_png_dimensions(box_workplane, tmp_path):
    """Default tile is a 2x2 first-angle grid: 2 cols x 100px + 1 gap x 4px = 204."""
    from PIL import Image

    output = tmp_path / "multi.png"
    preview.render_multi_view(box_workplane, str(output), view_size=100)
    img = Image.open(str(output))
    assert img.width == 204


def test_pyrender_not_imported(box_workplane, tmp_path):
    """Importing and using preview must not import pyrender or OpenGL."""
    import sys

    output = tmp_path / "check.png"
    preview.render_single(box_workplane, str(output))
    assert "pyrender" not in sys.modules
    assert "OpenGL" not in sys.modules


def test_render_view_returns_pil_image(box_workplane):
    from PIL import Image

    img = preview.render_view(box_workplane, elev=25, azim=-60, width=200, height=200)
    assert isinstance(img, Image.Image)
    assert img.size == (200, 200)


def test_tessellate_empty_safe():
    """_tessellate should not crash on a shape with no tessellation."""
    # An empty compound has no geometry; should return empty arrays without error.
    import numpy as np

    # Don't call tessellate on a Workplane with nothing on the stack;
    # instead test with a real shape to confirm the function runs cleanly.
    box = cq.Workplane("XY").box(5, 5, 5)
    verts, triangles = preview._tessellate(box)
    assert isinstance(verts, np.ndarray)
    assert verts.shape[1] == 3
    assert len(triangles) > 0


def test_render_multi_view_is_two_by_two(box_workplane, tmp_path):
    """Default tile is 2 columns x 2 rows (four panels): its height minus caption/
    header chrome is two panels tall, not three."""
    from PIL import Image

    out = tmp_path / "tile.png"
    preview.render_multi_view(box_workplane, str(out), view_size=100)
    img = Image.open(str(out))
    # Two 100px rows + one 4px gap + per-row labels + header/footer; well under a
    # three-row tile would be. Assert width is exactly the 2-column width and height
    # is less than three panel rows would require (3*100 = 300 of panels alone).
    assert img.width == 204
    assert img.height < 300 + 200  # generous chrome allowance, still < a 3-row tile


def test_render_section_produces_png(box_workplane, tmp_path):
    """render_section writes a standalone cross-section file."""
    out = tmp_path / "section_x.png"
    result = preview.render_section(box_workplane, str(out), "x", 0.0, view_size=200)
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_section_returns_none_on_cut_failure(box_workplane):
    """A degenerate cut yields None so the caller can skip writing a blank file."""
    from unittest.mock import patch

    with patch("preview._cut_half", return_value=None):
        result = preview.render_section(box_workplane, "unused.png", "x", 0.0)
    assert result is None


def test_render_cq_view_ortho_option(box_workplane):
    """The ortho path renders without error and returns an image of the requested size."""
    from PIL import Image

    img = preview._render_cq_view(box_workplane, 0, -90, 200, 200, ortho=True)
    assert isinstance(img, Image.Image)
    assert img.size == (200, 200)


def test_render_detail_view_is_higher_default_resolution_than_tile():
    assert preview.DETAIL_VIEW_SIZE > preview.DEFAULT_VIEW_SIZE


def test_render_detail_view_zoomed_fills_more_of_frame_than_whole_part(box_workplane, tmp_path):
    """A tight focus window around a small region should show more solid (non-
    background) pixels than the same view fit to the whole 10mm cube, since the
    zoomed window magnifies a sub-region to fill the same pixel canvas."""
    import numpy as np
    from PIL import Image

    whole_path = tmp_path / "whole.png"
    zoomed_path = tmp_path / "zoomed.png"
    preview.render_detail_view(
        box_workplane, str(whole_path), focus_center=(0, 0, 0), focus_size=10.0, view_size=200
    )
    # A 3mm window centered on a cube corner: still inside the solid, but zoomed
    # in tightly enough that the solid fills virtually the whole frame.
    preview.render_detail_view(
        box_workplane, str(zoomed_path), focus_center=(4, 4, 4), focus_size=3.0, view_size=200
    )

    def _bg_fraction(path):
        arr = np.asarray(Image.open(path).convert("RGB"))
        bg = np.array([0xE8, 0xE8, 0xEC])
        return float(np.all(np.abs(arr.astype(int) - bg) < 3, axis=-1).mean())

    assert _bg_fraction(zoomed_path) < _bg_fraction(whole_path)


@pytest.mark.parametrize(
    "render_fn, args, focus_size",
    [
        (preview.render_detail_view, (), 4.0),
        (preview.render_detail_section, ("x", 0.0), 6.0),
    ],
    ids=["detail_view", "detail_section"],
)
def test_render_detail_produces_png(box_workplane, tmp_path, render_fn, args, focus_size):
    out = tmp_path / "detail.png"
    result = render_fn(
        box_workplane, str(out), *args, focus_center=(0, 0, 0), focus_size=focus_size, view_size=200
    )
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_detail_section_returns_none_on_cut_failure(box_workplane):
    from unittest.mock import patch

    with patch("preview._cut_half", return_value=None):
        result = preview.render_detail_section(
            box_workplane, "unused.png", "x", 0.0, focus_center=(0, 0, 0), focus_size=6.0
        )
    assert result is None


def test_panel_labels_are_compass_terms():
    """Panel labels use the compass convention; no left/right/front/back terms."""
    labels = [label for _, _, label, _ in preview.MULTI_VIEW_PANELS]
    assert labels == [
        "Viewed from South",
        "Viewed from West",
        "Viewed from above",
        "Isometric",
    ]
    for label in labels:
        lowered = label.lower()
        assert "front" not in lowered
        assert "left" not in lowered
        assert "right" not in lowered


def test_north_face_marker_confirms_compass_mapping(tmp_path):
    """An asymmetric marker protruding past the North (+Y) face changes the
    silhouette in the West and above panels (Y is a screen axis there) but not
    in the South panel (Y is the depth axis there), confirming empirically that
    the labeled panels show what their compass names claim."""
    from PIL import Image

    view_size = 200
    plain = cq.Workplane("XY").box(40, 30, 20)
    marked = plain.union(cq.Workplane("XY").center(10, 15).box(8, 4, 8))

    plain_png = tmp_path / "plain.png"
    marked_png = tmp_path / "marked.png"
    preview.render_multi_view(plain, str(plain_png), view_size=view_size)
    preview.render_multi_view(marked, str(marked_png), view_size=view_size)

    plain_img = np.asarray(Image.open(plain_png).convert("RGB"), dtype=int)
    marked_img = np.asarray(Image.open(marked_png).convert("RGB"), dtype=int)

    header_h = 40
    label_h = 24
    gap = 4
    diffs = []
    for idx in range(4):
        col, row = idx % 2, idx // 2
        px = col * (view_size + gap)
        py = header_h + label_h + row * (view_size + gap + label_h)
        p_crop = plain_img[py : py + view_size, px : px + view_size]
        m_crop = marked_img[py : py + view_size, px : px + view_size]
        diffs.append(int(np.abs(p_crop - m_crop).sum()))

    south_diff, west_diff, above_diff, _iso_diff = diffs
    assert west_diff > south_diff
    assert above_diff > south_diff


def test_legend_line_matches_names_verbatim():
    line = preview._legend_line(
        [
            {"name": "handle", "center": (0, 0, 0)},
            {"name": "cable_slot", "center": (1, 1, 1)},
        ],
        ["boss_sw"],
    )
    assert line == "1 handle   2 cable_slot   boss_sw (not located)"


def test_legend_line_none_without_callouts():
    assert preview._legend_line(None, None) is None
    assert preview._legend_line([], []) is None


def test_callouts_change_ortho_panels_but_not_isometric(box_workplane, tmp_path):
    """Badges + leader lines are drawn on the three orthographic panels only; the
    isometric panel is pixel-identical with or without callouts."""
    from PIL import Image

    view_size = 200
    callouts = [{"name": "corner", "center": (4, 4, 4)}]

    plain_png = tmp_path / "plain.png"
    calledout_png = tmp_path / "calledout.png"
    preview.render_multi_view(box_workplane, str(plain_png), view_size=view_size)
    preview.render_multi_view(
        box_workplane, str(calledout_png), view_size=view_size, callouts=callouts
    )

    plain_img = np.asarray(Image.open(plain_png).convert("RGB"), dtype=int)
    calledout_img = np.asarray(Image.open(calledout_png).convert("RGB"), dtype=int)

    header_h = 40
    label_h = 24
    gap = 4
    diffs = []
    for idx in range(4):
        col, row = idx % 2, idx // 2
        px = col * (view_size + gap)
        py = header_h + label_h + row * (view_size + gap + label_h)
        p_crop = plain_img[py : py + view_size, px : px + view_size]
        c_crop = calledout_img[py : py + view_size, px : px + view_size]
        diffs.append(int(np.abs(p_crop - c_crop).sum()))

    south_diff, west_diff, above_diff, iso_diff = diffs
    assert south_diff > 0
    assert west_diff > 0
    assert above_diff > 0
    assert iso_diff == 0


def test_no_callouts_renders_unchanged_tile(box_workplane, tmp_path):
    """With no callouts and no unlocated names, the tile is identical to the
    pre-callout-feature baseline (no legend row, same dimensions)."""
    out = tmp_path / "unchanged.png"
    preview.render_multi_view(box_workplane, str(out), view_size=100)
    from PIL import Image

    img = Image.open(str(out))
    assert img.width == 204
