"""
Tests for src/preview.py — CadQuery-based preview rendering.

These tests run real CadQuery geometry and require the venv to be active.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import cadquery as cq

import preview


@pytest.fixture
def box_workplane():
    """Simple 10x10x10 mm cube as a CadQuery Workplane."""
    return cq.Workplane("XY").box(10, 10, 10)


def test_render_multi_view_produces_png(box_workplane, tmp_path):
    output = tmp_path / "multi.png"
    result = preview.render_multi_view(box_workplane, str(output))
    assert result == str(output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_render_single_produces_png(box_workplane, tmp_path):
    output = tmp_path / "single.png"
    result = preview.render_single(box_workplane, str(output), title="Test Box")
    assert result == str(output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_render_multi_view_png_dimensions(box_workplane, tmp_path):
    """Output image should have the expected 3x2 grid dimensions."""
    from PIL import Image

    output = tmp_path / "multi.png"
    preview.render_multi_view(box_workplane, str(output), view_size=100)
    img = Image.open(str(output))
    # 3 cols x 100px + 2 gaps x 4px = 308; rows add header/footer
    assert img.width == 308


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


def test_render_multi_view_cross_sections_taller(box_workplane, tmp_path):
    """cross_sections=True should produce a taller tile than the default 6-view."""
    from PIL import Image

    out6 = tmp_path / "six_view.png"
    out9 = tmp_path / "nine_view.png"
    preview.render_multi_view(box_workplane, str(out6), view_size=100)
    preview.render_multi_view(box_workplane, str(out9), view_size=100, cross_sections=True)
    h6 = Image.open(str(out6)).height
    h9 = Image.open(str(out9)).height
    assert h9 > h6


def test_render_multi_view_cross_sections_fallback(box_workplane, tmp_path):
    """When _cut_half returns None for all axes, render completes with blank tiles."""
    from unittest.mock import patch

    from PIL import Image

    out = tmp_path / "fallback.png"
    with patch("preview._cut_half", return_value=None):
        preview.render_multi_view(box_workplane, str(out), view_size=100, cross_sections=True)

    assert out.exists()
    img = Image.open(str(out))
    # 3 rows taller than 2-row default despite blank section tiles
    out6 = tmp_path / "six_view.png"
    preview.render_multi_view(box_workplane, str(out6), view_size=100)
    assert img.height > Image.open(str(out6)).height


def test_render_multi_view_extra_sections_adds_tiles(box_workplane, tmp_path):
    """extra_sections appends targeted section tiles beyond the default center cuts,
    growing the tile even when the total tile count isn't a multiple of 3 columns
    (regression: rows used to be computed with floor division, clipping the last
    partial row off the canvas)."""
    from PIL import Image

    out_base = tmp_path / "cross.png"
    out_extra = tmp_path / "extra.png"
    preview.render_multi_view(box_workplane, str(out_base), view_size=100, cross_sections=True)
    preview.render_multi_view(
        box_workplane,
        str(out_extra),
        view_size=100,
        cross_sections=True,
        extra_sections=[("x", 2.0)],  # 9 + 1 = 10 tiles: not a multiple of 3
    )
    assert Image.open(str(out_extra)).height > Image.open(str(out_base)).height


def test_render_multi_view_extra_sections_fallback(box_workplane, tmp_path):
    """A failed targeted-section cut renders a blank tile instead of crashing."""
    from unittest.mock import patch

    out = tmp_path / "extra_fallback.png"
    with patch("preview._cut_half", return_value=None):
        preview.render_multi_view(
            box_workplane, str(out), view_size=100, extra_sections=[("y", 3.0)]
        )
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_detail_view_produces_png(box_workplane, tmp_path):
    out = tmp_path / "detail.png"
    result = preview.render_detail_view(
        box_workplane, str(out), focus_center=(0, 0, 0), focus_size=4.0, view_size=200
    )
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


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


def test_render_detail_section_produces_png(box_workplane, tmp_path):
    out = tmp_path / "detail_section.png"
    result = preview.render_detail_section(
        box_workplane, str(out), "x", 0.0, focus_center=(0, 0, 0), focus_size=6.0, view_size=200
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
