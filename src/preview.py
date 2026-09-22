#!/usr/bin/env python3
"""
Render preview images of a CadQuery model for visual inspection.

Renders using CadQuery tessellation and matplotlib (Agg backend).
No OpenGL or display server required.

Usage (via render_preview.py subprocess):
    python3 render_preview.py model.py --output preview.png
    python3 render_preview.py model.py --views iso

Public API:
    render_single(workplane, output_path, title, width, height)
    render_multi_view(workplane, output_path, title, subtitle, view_size)
    render_section(workplane, output_path, axis, position, view_size)
    render_detail_view(workplane, output_path, focus_center, focus_size)
    render_detail_section(workplane, output_path, axis, position, focus_center, focus_size)

All functions accept a CadQuery Workplane or Shape as the first argument.
`render_detail_view`/`render_detail_section` are standalone, high-resolution,
zoomed-in renders for a single small feature (a boss, hole, tab) that would be
imperceptible in the default whole-part framing -- see DETAIL_VIEW_SIZE.
"""

import os
import sys

import cadquery as cq
import mpl_toolkits.mplot3d  # noqa: F401 -- registers the '3d' projection
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw, ImageFont

# Cycled leader-line offsets (screen points) so badges near the same projected
# area don't stack directly on top of each other.
_CALLOUT_OFFSETS = [(20, 20), (-20, 20), (20, -20), (-20, -20)]

# (elev, azim, label, ortho) for the default 2x2 tile. Labels name the compass
# viewing station per prompts/planning.md (North=+Y, East=+X, up=+Z), verified
# empirically against an asymmetric fixture -- see render_multi_view's docstring.
MULTI_VIEW_PANELS = [
    (0, -90, "Viewed from South", True),
    (0, 180, "Viewed from West", True),
    (90, -90, "Viewed from above", True),
    (25, -60, "Isometric", False),
]

DEFAULT_VIEW_SIZE = 600
# Higher resolution for standalone feature-detail renders so a small feature is
# actually legible when zoomed in, unlike the compact overview-tile thumbnails.
DETAIL_VIEW_SIZE = 1400
_SINGLE_WIDTH = 900
_SINGLE_HEIGHT = 750
_BG_COLOR = "#E8E8EC"


# ---------------------------------------------------------------------------
# CQ geometry helpers
# ---------------------------------------------------------------------------


def _get_shape(wp):
    """Return a CadQuery Shape from a Workplane, Assembly, or pass-through."""
    if isinstance(wp, cq.Workplane):
        return wp.val()
    if hasattr(wp, "toCompound"):  # cq.Assembly
        return wp.toCompound()
    return wp


def _tessellate(wp, tolerance=0.05):
    """Tessellate CadQuery geometry for matplotlib rendering.

    Returns (verts, triangles) where:
        verts: np.ndarray of shape (N, 3)
        triangles: list of (3, 3) float arrays suitable for Poly3DCollection
    """
    shape = _get_shape(wp)
    raw_verts, raw_faces = shape.tessellate(tolerance, angularTolerance=0.1)
    if not raw_verts or not raw_faces:
        return np.zeros((0, 3), dtype=float), []
    verts = np.array([[v.x, v.y, v.z] for v in raw_verts], dtype=float)
    triangles = [verts[list(f)] for f in raw_faces]
    return verts, triangles


def _bbox_info(wp):
    """Return (ext_x, ext_y, ext_z, vol_cm3) from CadQuery bounding box and volume."""
    shape = _get_shape(wp)
    try:
        bb = shape.BoundingBox()
        ext_x = bb.xmax - bb.xmin
        ext_y = bb.ymax - bb.ymin
        ext_z = bb.zmax - bb.zmin
    except Exception:
        ext_x = ext_y = ext_z = 0.0
    try:
        vol_cm3 = abs(shape.Volume()) / 1000.0
    except Exception:
        vol_cm3 = None
    return ext_x, ext_y, ext_z, vol_cm3


def _shade_triangles(triangles):
    """Compute per-face flat-shading colors using a fixed light direction.

    Returns a list of RGB tuples for use as Poly3DCollection facecolors.
    """
    light = np.array([1.0, 1.0, 2.0])
    light = light / np.linalg.norm(light)
    base = np.array([0.42, 0.62, 0.92])  # medium blue
    ambient = 0.35

    colors = []
    for tri in triangles:
        v0, v1, v2 = tri
        normal = np.cross(v1 - v0, v2 - v0)
        n_len = np.linalg.norm(normal)
        if n_len > 0:
            normal = normal / n_len
        diffuse = max(0.0, float(np.dot(normal, light)))
        intensity = ambient + (1.0 - ambient) * diffuse
        colors.append(tuple(np.clip(base * intensity, 0, 1)))
    return colors


def _cut_half(shape, axis: str, center: float, remove_positive: bool = True):
    """Return shape with one half removed by an axis-aligned plane at center.

    remove_positive=True removes the half where the axis coordinate > center.
    remove_positive=False removes the half where the axis coordinate < center.
    Returns a CadQuery Shape, or None on OCC failure.
    """
    try:
        bb = shape.BoundingBox()
        span = max(bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin, 1.0) * 4
        cx = (bb.xmax + bb.xmin) / 2
        cy = (bb.ymax + bb.ymin) / 2
        cz = (bb.zmax + bb.zmin) / 2
        sign = 1 if remove_positive else -1
        if axis == "x":
            tx, ty, tz = center + sign * span / 2, cy, cz
        elif axis == "y":
            tx, ty, tz = cx, center + sign * span / 2, cz
        else:
            tx, ty, tz = cx, cy, center + sign * span / 2
        cutter = cq.Workplane().box(span, span, span).translate((tx, ty, tz)).val()
        return shape.cut(cutter)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------


def _get_font(size=14):
    """Try to load a sans-serif font, falling back to PIL default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _info_lines(wp, n_triangles, density_g_cm3=1.24, material="PLA"):
    """Two-line footer: dimensions + volume; triangle count + weight estimate."""
    ext_x, ext_y, ext_z, vol_cm3 = _bbox_info(wp)
    line1 = f"Bounding box: {ext_x:.1f} x {ext_y:.1f} x {ext_z:.1f} mm"
    if vol_cm3 is not None:
        line1 += f"  |  Volume: {vol_cm3:.1f} cm³"
    line2 = f"Triangles: {n_triangles:,}"
    if vol_cm3 is not None:
        weight_g = vol_cm3 * density_g_cm3
        line2 += f"  |  {material} estimate: ~{weight_g:.0f} g"
    return line1, line2


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _draw_callouts(ax, callouts):
    """Draw a numbered badge + leader line at each callout's projected 2D position.

    Projects each callout's authored-frame `center` through the panel's own live
    camera (`ax.get_proj()`) -- pure 3D-to-2D projection, no vision or heuristic
    placement (design D2). Badge numbers follow `callouts` order (1-based).
    """
    proj = ax.get_proj()
    for i, callout in enumerate(callouts, start=1):
        cx, cy, cz = callout["center"]
        x2, y2, _ = proj3d.proj_transform(cx, cy, cz, proj)
        dx, dy = _CALLOUT_OFFSETS[(i - 1) % len(_CALLOUT_OFFSETS)]
        ax.annotate(
            str(i),
            xy=(x2, y2),
            xycoords="data",
            xytext=(dx, dy),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="black",
            bbox={"boxstyle": "circle,pad=0.3", "fc": "#FFD400", "ec": "black", "lw": 1.2},
            arrowprops={
                "arrowstyle": "-",
                "color": "black",
                "lw": 1.1,
                "shrinkA": 0,
                "shrinkB": 6,
            },
            annotation_clip=False,
        )


def _render_cq_view(
    wp,
    elev,
    azim,
    width=DEFAULT_VIEW_SIZE,
    height=DEFAULT_VIEW_SIZE,
    focus=None,
    ortho=False,
    callouts=None,
):
    """Render one view of a CadQuery object. Returns a PIL Image (RGB).

    Uses FigureCanvasAgg directly so no display server or global pyplot
    state is needed.

    `focus` is an optional `(center_xyz, size_mm)` pair overriding the default
    whole-mesh-fit axis limits with a fixed-size cubic window centered on a point
    -- used for feature detail views where the feature is small relative to the
    whole part and would be imperceptible at the default whole-part framing.

    `ortho` selects true orthographic projection (parallel edges stay parallel, no
    perspective convergence). Used for the axis-aligned drei-tafel panels where an
    undistorted measured projection matters; the isometric panel leaves it False.

    `callouts`, when given, is a list of `{"name": str, "center": (x, y, z)}` --
    only meaningful when `ortho=True` (see `render_multi_view`); each draws a
    numbered badge via `_draw_callouts`.
    """
    verts, triangles = _tessellate(wp)

    dpi = 100
    fig = Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    fig.patch.set_facecolor(_BG_COLOR)

    ax = fig.add_subplot(111, projection="3d")
    if ortho:
        ax.set_proj_type("ortho")
    ax.set_facecolor(_BG_COLOR)

    if triangles:
        # NOTE: flat faces can show triangular bright/dark patches here. This is a
        # matplotlib mplot3d limitation, not a geometry or normals bug: mplot3d has
        # no z-buffer and depth-sorts whole triangles by average depth (painter's
        # algorithm). A steeply-shaded wall/fillet triangle occasionally sorts in
        # front of a coplanar flat-face triangle and paints over it. The exported
        # STL/3MF are watertight and winding-consistent, and _shade_triangles
        # computes correct per-face normals (a flat top face is uniformly +Z). The
        # artifact is cosmetic and confined to the preview. A real z-buffered
        # renderer would remove it -- see TODO ("preview: z-buffered renderer").
        face_colors = _shade_triangles(triangles)
        coll = Poly3DCollection(triangles, facecolors=face_colors, edgecolor="none")
        ax.add_collection3d(coll)

        if focus is not None:
            (mid_x, mid_y, mid_z), size = focus
            half = max(float(size), 1.0) * 0.6
        else:
            # Equal-aspect axis limits fit to the whole mesh
            x_range = verts[:, 0].max() - verts[:, 0].min()
            y_range = verts[:, 1].max() - verts[:, 1].min()
            z_range = verts[:, 2].max() - verts[:, 2].min()
            half = max(x_range, y_range, z_range, 1.0) * 0.6
            mid_x = (verts[:, 0].max() + verts[:, 0].min()) / 2
            mid_y = (verts[:, 1].max() + verts[:, 1].min()) / 2
            mid_z = (verts[:, 2].max() + verts[:, 2].min()) / 2
        ax.set_xlim(mid_x - half, mid_x + half)
        ax.set_ylim(mid_y - half, mid_y + half)
        ax.set_zlim(mid_z - half, mid_z + half)

    ax.view_init(elev=elev, azim=azim)
    if callouts and ortho:
        _draw_callouts(ax, callouts)
    ax.set_axis_off()

    canvas.draw()
    buf = canvas.buffer_rgba()
    img = Image.frombytes("RGBA", canvas.get_width_height(), bytes(buf))
    return img.convert("RGB")


def render_view(wp, elev, azim, width=DEFAULT_VIEW_SIZE, height=DEFAULT_VIEW_SIZE):
    """Render the model from a specific angle. Returns a PIL Image."""
    return _render_cq_view(wp, elev, azim, width, height)


def render_single(
    wp,
    output_path,
    title="Model Preview",
    width=_SINGLE_WIDTH,
    height=_SINGLE_HEIGHT,
    density_g_cm3=1.24,
    material="PLA",
):
    """Render a single isometric view with title and footer. Returns output_path."""
    _, triangles = _tessellate(wp)
    img = _render_cq_view(wp, elev=25, azim=-60, width=width, height=height)

    canvas = Image.new("RGB", (img.width, img.height + 100), "white")
    canvas.paste(img, (0, 40))
    draw = ImageDraw.Draw(canvas)

    title_font = _get_font(20)
    info_font = _get_font(13)
    line1, line2 = _info_lines(wp, len(triangles), density_g_cm3, material)

    draw.text((canvas.width // 2, 10), title, fill="black", font=title_font, anchor="mt")
    draw.text(
        (canvas.width // 2, canvas.height - 30),
        line1,
        fill="gray",
        font=info_font,
        anchor="mb",
    )
    draw.text(
        (canvas.width // 2, canvas.height - 10),
        line2,
        fill="gray",
        font=info_font,
        anchor="mb",
    )

    canvas.save(output_path)
    return output_path


_SECTION_CAMERA = {"x": (5, 0), "y": (5, -90), "z": (90, -90)}
_SECTION_REMOVE_POSITIVE = {"x": True, "y": False, "z": True}


def render_detail_view(
    wp,
    output_path,
    focus_center,
    focus_size,
    elev=25,
    azim=-60,
    view_size=DETAIL_VIEW_SIZE,
):
    """Render a single high-resolution, zoomed-in view of a small feature.

    `focus_center` is `(x, y, z)` in the part's authored frame and `focus_size` is
    the span (mm) of the cubic window to frame -- use roughly 2-4x the feature's
    own size so it's centered with some surrounding context, not the whole part's
    extent. Standalone file, not part of a tile: pair with a descriptive,
    feature-named `output_path` (see `run_cadquery_model.py --detail`).
    """
    img = _render_cq_view(
        wp, elev, azim, view_size, view_size, focus=(tuple(focus_center), focus_size)
    )
    img.save(output_path)
    return output_path


def render_detail_section(
    wp,
    output_path,
    axis,
    position,
    focus_center,
    focus_size,
    view_size=DETAIL_VIEW_SIZE,
):
    """Render a high-resolution, zoomed-in cross-section through a small feature.

    Cuts `wp` at `axis`/`position` (same convention as the targeted
    `--extra-section` cuts) and frames the result on `focus_center`/`focus_size`
    (see `render_detail_view`). Returns `output_path` on success, `None` if the
    cut fails (OCC failure on a degenerate cut plane) -- the caller should skip
    writing that file and warn rather than save a meaningless blank image under a
    feature-specific name.
    """
    shape = _get_shape(wp)
    sec = _cut_half(shape, axis, position, remove_positive=_SECTION_REMOVE_POSITIVE[axis])
    if sec is None:
        return None
    elev, azim = _SECTION_CAMERA[axis]
    img = _render_cq_view(
        sec, elev, azim, view_size, view_size, focus=(tuple(focus_center), focus_size)
    )
    img.save(output_path)
    return output_path


def render_section(wp, output_path, axis, position, view_size=DEFAULT_VIEW_SIZE):
    """Render a full cross-section cut at `axis`/`position` as a standalone file.

    Cuts `wp` with an axis-aligned half-space at `position` (same keep-side and
    camera convention as the in-tile sections used to use) and frames the whole cut
    body (no focus window, unlike `render_detail_section`). Returns `output_path` on
    success, `None` if the cut fails (OCC failure on a degenerate plane) so the
    caller can skip writing a meaningless blank file. Used by render_preview.py to
    write `--cross-sections` as separate files instead of tiles.
    """
    shape = _get_shape(wp)
    sec = _cut_half(shape, axis, position, remove_positive=_SECTION_REMOVE_POSITIVE[axis])
    if sec is None:
        return None
    elev, azim = _SECTION_CAMERA[axis]
    img = _render_cq_view(sec, elev, azim, view_size, view_size)
    img.save(output_path)
    return output_path


def _legend_line(callouts, unlocated_names):
    """Caption legend row mapping badge numbers to names, or None if no callouts."""
    if not callouts and not unlocated_names:
        return None
    parts = [f"{i} {c['name']}" for i, c in enumerate(callouts or [], start=1)]
    parts += [f"{name} (not located)" for name in (unlocated_names or [])]
    return "   ".join(parts)


def render_multi_view(
    wp,
    output_path,
    title="Model Preview",
    subtitle=None,
    view_size=DEFAULT_VIEW_SIZE,
    callouts=None,
    unlocated_names=None,
    density_g_cm3=1.24,
    material="PLA",
):
    """Render the default 2x2 first-angle (DIN) projection tile.

    Panels, in first-angle placement (South above above-view, West view drawn on the
    right), labeled with the compass viewing station per `prompts/planning.md`
    (North=+Y, East=+X, up=+Z) and verified empirically against an asymmetric
    fixture -- not derived from prose, since the camera-to-compass mapping is not
    obvious from the elev/azim values alone:

        Viewed from South (camera south of the part, looking North) top-left    [orthographic]
        Viewed from West  (camera west of the part, looking East)   top-right   [orthographic]
        Viewed from above (camera above, looking down)              bottom-left [orthographic]
        Isometric                                                   bottom-right [pictorial]

    The three orthographic panels use true orthographic projection with exact
    axis-aligned cameras (no perspective tilt) so edges stay undistorted; the
    isometric panel keeps a pictorial view for the 3D read. Overall bounding box,
    volume, triangle count, and PLA estimate are shown in the caption -- no
    dimension lines are drawn on the panels. Cross-sections are no longer part of
    this tile; they are rendered as separate files (see render_preview.py
    --cross-sections).

    `callouts`, when given, is a list of `{"name": str, "center": (x, y, z)}`
    (authored frame) -- each gets a numbered badge + leader line on the three
    orthographic panels only (not isometric), and a caption legend line mapping
    badge numbers to names, in supply order. `unlocated_names` are named features
    with no known position: listed in the legend unbadged as "name (not located)"
    so the tile still carries the complete agreed vocabulary. Neither argument
    changes anything when omitted.
    """
    legend_line = _legend_line(callouts, unlocated_names)

    _, triangles = _tessellate(wp)
    images = [
        (
            _render_cq_view(
                wp,
                elev,
                azim,
                view_size,
                view_size,
                ortho=ortho,
                callouts=callouts if ortho else None,
            ),
            label,
        )
        for elev, azim, label, ortho in MULTI_VIEW_PANELS
    ]

    cols = 2
    rows = (len(images) + cols - 1) // cols
    gap = 4
    header_h = 40 + (20 if subtitle else 0)
    footer_h = 55 + (20 if legend_line else 0)
    label_h = 24
    w = view_size * cols + gap * (cols - 1)
    h = view_size * rows + gap * (rows - 1) + header_h + footer_h + label_h * rows

    canvas = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(canvas)

    title_font = _get_font(20)
    subtitle_font = _get_font(14)
    label_font = _get_font(14)
    info_font = _get_font(13)

    draw.text((w // 2, 12), title, fill="black", font=title_font, anchor="mt")
    if subtitle:
        draw.text((w // 2, 34), subtitle, fill="#666666", font=subtitle_font, anchor="mt")

    for idx, (img, label) in enumerate(images):
        col = idx % cols
        row = idx // cols
        px = col * (view_size + gap)
        py = header_h + label_h + row * (view_size + gap + label_h)
        canvas.paste(img, (px, py))
        draw.text(
            (px + view_size // 2, py - 4),
            label,
            fill="#444444",
            font=label_font,
            anchor="mb",
        )

    line1, line2 = _info_lines(wp, len(triangles), density_g_cm3, material)
    if legend_line:
        draw.text((w // 2, h - 50), line1, fill="gray", font=info_font, anchor="mb")
        draw.text((w // 2, h - 30), line2, fill="gray", font=info_font, anchor="mb")
        draw.text((w // 2, h - 10), legend_line, fill="#333333", font=info_font, anchor="mb")
    else:
        draw.text((w // 2, h - 30), line1, fill="gray", font=info_font, anchor="mb")
        draw.text((w // 2, h - 10), line2, fill="gray", font=info_font, anchor="mb")

    canvas.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI (for quick manual testing)
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Render a CadQuery model script preview (run via render_preview.py)"
    )
    parser.add_argument(
        "--help-note",
        action="store_true",
        help="Show usage note",
    )
    parser.parse_args()
    print(
        "preview.py is a library. Use render_preview.py to render from a model script.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
