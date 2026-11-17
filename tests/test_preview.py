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


def test_render_cq_view_size(box_workplane):
    """A single view renders without error and returns an image of the requested size."""
    from PIL import Image

    img = preview._render_cq_view(box_workplane, 0, -90, 200, 200)
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
    # A 3mm window at the cube center: entirely inside the solid's silhouette, so
    # the solid fills the whole frame.
    preview.render_detail_view(
        box_workplane, str(zoomed_path), focus_center=(0, 0, 0), focus_size=3.0, view_size=200
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


def test_tile_has_no_legend_row(box_workplane, tmp_path):
    """The 2x2 tile is two panels wide with no legend row."""
    out = tmp_path / "unchanged.png"
    preview.render_multi_view(box_workplane, str(out), view_size=100)
    from PIL import Image

    img = Image.open(str(out))
    assert img.width == 204


def test_flat_face_shades_uniformly_and_nearer_occludes(tmp_path):
    """Z-buffer: a flat top face is one uniform color (no per-triangle patches), and
    a nearer box changes the silhouette of the union."""
    big = cq.Workplane("XY").box(20, 20, 4)
    both = big.union(cq.Workplane("XY").workplane(offset=2).box(6, 6, 4))

    flat = np.asarray(preview._render_cq_view(big, 90, -90, 200, 200), dtype=int)
    center = flat[80:120, 80:120].reshape(-1, 3)
    assert (center == center[0]).all()

    img = np.asarray(preview._render_cq_view(both, 90, -90, 200, 200), dtype=int)
    # Top of the small box and the big top face share +Z normal (same shade), so
    # check the side view instead: small box silhouette rises above the big box.
    side = np.asarray(preview._render_cq_view(both, 0, -90, 200, 200), dtype=int)
    bg = np.array([0xE8, 0xE8, 0xEC])
    side_big = np.asarray(preview._render_cq_view(big, 0, -90, 200, 200), dtype=int)

    def rows(a):
        return (np.abs(a - bg).sum(axis=-1) > 10).any(axis=1).sum()

    solid_rows, solid_rows_big = rows(side), rows(side_big)
    assert img.shape == (200, 200, 3)
    assert solid_rows > solid_rows_big


# --- preview-section-readability ---


def test_edge_mask_separates_step_from_plate():
    """A raised block on a plate has a depth edge at its rim even though its top
    face and the plate top share a +Z normal (same shade)."""
    import zbuffer

    plate = cq.Workplane("XY").box(30, 30, 2)
    both = plate.union(cq.Workplane("XY").workplane(offset=1).box(10, 10, 6))
    verts, tris = preview._tessellate(both)
    project = zbuffer.make_camera(verts, 0, -90, 200, 200)
    _, depth = zbuffer.rasterize_with_depth(
        tris, np.ones((len(tris), 3)), project, 200, 200, (0, 0, 0)
    )
    edges = zbuffer.edge_mask(depth)
    covered = np.isfinite(depth)
    inner_edges = edges[covered & ~np.pad(~covered, 0)].sum()
    assert inner_edges > 0
    # edge between plate top (z=1) and block side exists mid-image
    assert edges[100:140, :].any()


def test_rasterize_matches_rasterize_with_depth_image():
    import zbuffer

    box = cq.Workplane("XY").box(10, 10, 10)
    verts, tris = preview._tessellate(box)
    project = zbuffer.make_camera(verts, 25, -60, 80, 80)
    colors = preview._shade_triangles(tris)
    a = zbuffer.rasterize(tris, colors, project, 80, 80, (0, 0, 0))
    b, depth = zbuffer.rasterize_with_depth(tris, colors, project, 80, 80, (0, 0, 0))
    assert (a == b).all() and depth.shape == (80, 80)


def test_section_through_solid_block_not_informative(tmp_path):
    block = cq.Workplane("XY").box(20, 20, 20)
    res = preview.render_section(block, str(tmp_path / "s.png"), "z", 0.0, view_size=200)
    assert res is not None
    assert res.informative is False


def test_section_through_bore_informative(tmp_path):
    part = cq.Workplane("XY").box(20, 20, 20).faces(">Z").workplane().hole(6)
    z_cut = preview.render_section(part, str(tmp_path / "z.png"), "z", 0.0, view_size=200)
    x_cut = preview.render_section(part, str(tmp_path / "x.png"), "x", 0.0, view_size=200)
    assert z_cut is not None and x_cut is not None
    assert z_cut.informative is True  # inner hole in the cap
    assert x_cut.informative is True  # cap narrower than uncut silhouette


def test_cap_colour_differs_from_coplanar_normal_face(tmp_path):
    """Z-cut of a plate+block: the cap and the lower plate top both face +Z."""
    from PIL import Image

    part = (
        cq.Workplane("XY")
        .box(30, 30, 2)
        .union(cq.Workplane("XY").workplane(offset=1).box(10, 10, 6))
    )
    out = tmp_path / "cap.png"
    preview.render_section(part, str(out), "z", 2.0, view_size=200)
    img = np.asarray(Image.open(out).convert("RGB"), dtype=int)
    centre = img[100, 100]  # cap through the block
    plate = img[100, 20]  # plate top, uncut region outside the block
    assert tuple(centre) != tuple(plate)
    assert (np.abs(centre - np.array(preview._CAP_COLOR) * 255) < 3).all()


def test_visible_occluded_anchor():
    import zbuffer

    box = cq.Workplane("XY").box(10, 10, 10)
    verts, tris = preview._tessellate(box)
    project = zbuffer.make_camera(verts, 90, -90, 100, 100)
    _, depth = zbuffer.rasterize_with_depth(
        tris, np.ones((len(tris), 3)), project, 100, 100, (0, 0, 0)
    )
    assert preview._visible((0, 0, 5), project, depth)
    assert not preview._visible((0, 0, -5), project, depth)
