#!/usr/bin/env python3
"""
Render preview images of a CadQuery model for visual inspection.

Renders using CadQuery tessellation and a numpy z-buffer rasterizer (zbuffer.py).
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
    render_feature_view / render_feature_section(workplane, output_path, frame, anchor)
    render_sheet(tiles, output_path, title, not_shown, not_located)

All functions accept a CadQuery Workplane or Shape as the first argument.
`render_detail_view`/`render_detail_section` are standalone, high-resolution,
zoomed-in renders for a single small feature (a boss, hole, tab) that would be
imperceptible in the default whole-part framing -- see DETAIL_VIEW_SIZE.
"""

import os
import sys

import cadquery as cq
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import zbuffer
from feature_frame import FLAT_DEPTH_MM

# Cycled leader-line offsets (pixels at the default view size) so badges near the same projected
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
    """Tessellate CadQuery geometry for rasterizing.

    Returns (verts, triangles) where:
        verts: np.ndarray of shape (N, 3)
        triangles: np.ndarray of shape (n, 3, 3)
    """
    shape = _get_shape(wp)
    raw_verts, raw_faces = shape.tessellate(tolerance, angularTolerance=0.1)
    if not raw_verts or not raw_faces:
        return np.zeros((0, 3), dtype=float), np.zeros((0, 3, 3), dtype=float)
    verts = np.array([[v.x, v.y, v.z] for v in raw_verts], dtype=float)
    return verts, verts[np.array(raw_faces)]


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

    Returns an (n, 3) float array of RGB colors in 0..1.
    """
    light = np.array([1.0, 1.0, 2.0])
    light = light / np.linalg.norm(light)
    base = np.array([0.42, 0.62, 0.92])  # medium blue
    ambient = 0.35

    normal = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    n_len = np.linalg.norm(normal, axis=1, keepdims=True)
    normal = np.divide(normal, n_len, out=np.zeros_like(normal), where=n_len > 0)
    diffuse = np.maximum(0.0, normal @ light)
    intensity = ambient + (1.0 - ambient) * diffuse
    return np.clip(base * intensity[:, None], 0, 1)


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


def _draw_callouts(img, badges):
    """Draw a numbered badge + leader line at each projected 2D position.

    `badges` is a list of `(number, (x, y))` -- pure 3D-to-2D projection, no vision or
    heuristic placement (design D2). Leader offsets cycle with the badge number.
    """
    draw = ImageDraw.Draw(img)
    k = img.width / DEFAULT_VIEW_SIZE
    font = _get_font(max(int(14 * k), 8))
    rad = 11 * k
    for num, (x, y) in badges:
        dx, dy = _CALLOUT_OFFSETS[(num - 1) % len(_CALLOUT_OFFSETS)]
        bx, by = x + dx * k, y - dy * k
        draw.line([(x, y), (bx, by)], fill="black", width=max(int(k), 1))
        draw.ellipse(
            [bx - rad, by - rad, bx + rad, by + rad], fill="#FFD400", outline="black", width=2
        )
        draw.text((bx, by), str(num), fill="black", font=font, anchor="mm")


_CAP_COLOR = np.array([0.95, 0.55, 0.15])
_EDGE_RGB = (40, 40, 50)
_VISIBLE_TOL = 0.01
_MERGE_PX = 12


class SectionPath(str):
    """Output path of a section render; `.informative` is False when the cap shows no
    hole, notch or void (advisory, not a gate)."""

    informative: bool | None
    cut: tuple[str, float] | None

    def __new__(cls, path, informative):
        obj = super().__new__(cls, path)
        obj.informative = informative
        obj.cut = None
        return obj


def _on_plane(triangles, axis, pos, tol=1e-3):
    """Boolean mask of triangles whose vertices all lie on the axis-aligned plane."""
    coord = triangles[:, :, "xyz".index(axis)]
    return (np.abs(coord - pos) < tol).all(axis=1)


def _mask(triangles, project, width, height):
    """Coverage mask of `triangles` in a camera (no shading)."""
    if len(triangles) == 0:
        return np.zeros((height, width), dtype=bool)
    white = np.ones((len(triangles), 3))
    arr = zbuffer.rasterize(triangles, white, project, width, height, (0, 0, 0))
    return arr[:, :, 0] > 127


def _has_inner_hole(mask):
    """True if `mask` has background pixels not connected to the image border."""
    step = max(1, max(mask.shape) // 256)
    solid = np.pad(mask[::step, ::step], 1)
    reach = np.zeros_like(solid)
    reach[0, :] = reach[-1, :] = reach[:, 0] = reach[:, -1] = True
    reach &= ~solid
    while True:
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= ~solid
        if (grown == reach).all():
            return bool((~solid & ~reach).any())
        reach = grown


def _cap_info(cap_tris, uncut_wp, project, width, height):
    """Return (cap_mask, informative): cap smaller than the uncut silhouette or holed."""
    cap_mask = _mask(cap_tris, project, width, height)
    _, uncut_tris = _tessellate(uncut_wp)
    sil = _mask(uncut_tris, project, width, height)
    cap_px = int(cap_mask.sum())
    informative = bool(cap_px > 0 and (cap_px < 0.98 * sil.sum() or _has_inner_hole(cap_mask)))
    return cap_mask, informative


def _render_panel(wp, elev, azim, width, height, focus=None, cap=None, uncut=None):
    """Render one view. Returns `(PIL image, project, depth buffer, informative)`.

    `cap=(axis, pos)` colours triangles lying on that plane distinctly and outlines
    them; with `uncut` (the shape before the cut) `informative` reports whether the
    cap differs from the uncut silhouette (None when not a section).
    """
    verts, triangles = _tessellate(wp)
    bg = tuple(int(_BG_COLOR[i : i + 2], 16) for i in (1, 3, 5))
    if len(triangles) == 0:
        return Image.new("RGB", (width, height), bg), None, None, None

    project = zbuffer.make_camera(verts, elev, azim, width, height, focus)
    colors = _shade_triangles(triangles)
    on_cap = _on_plane(triangles, *cap) if cap else None
    if cap:
        colors[on_cap] = _CAP_COLOR
    arr, depth = zbuffer.rasterize_with_depth(triangles, colors, project, width, height, bg)
    arr[zbuffer.edge_mask(depth)] = _EDGE_RGB
    informative = None
    if cap:
        cap_mask, informative = _cap_info(triangles[on_cap], uncut, project, width, height)
        inner = cap_mask.copy()
        inner[1:-1, 1:-1] = (
            cap_mask[1:-1, 1:-1]
            & cap_mask[:-2, 1:-1]
            & cap_mask[2:, 1:-1]
            & cap_mask[1:-1, :-2]
            & cap_mask[1:-1, 2:]
        )
        arr[cap_mask & ~inner] = _EDGE_RGB
    return Image.fromarray(arr, "RGB"), project, depth, informative


def _visible(center, project, depth):
    """Z-buffer visibility test: is `center` inside the frame and not occluded?"""
    x, y, z = project(center)
    h, w = depth.shape
    ix, iy = int(x), int(y)
    if not (0 <= ix < w and 0 <= iy < h):
        return False
    covered = np.isfinite(depth)
    if not covered.any():
        return True
    tol = max(_VISIBLE_TOL * float(depth[covered].max() - depth[covered].min()), 1e-3)
    return bool(z >= depth[iy, ix] - tol)


def _draw_marker(img, project, depth, anchor):
    """Badge `anchor` (build-pose xyz) on `img` when it is inside the frame and unoccluded."""
    if anchor is not None and project is not None and _visible(anchor, project, depth):
        _draw_callouts(img, [(1, tuple(project(anchor)[:2]))])


def _place_callouts(callouts, panels, view_size):
    """Assign each callout to the first panel where it is visible, merging near badges.

    `panels` is a list of `(project, depth)` in preference order. Returns
    `(badges_per_panel, legend_callouts, hidden_names)`: badges as `(number, (x, y))`
    per panel, legend entries as `{"name"}` dicts (`"name xN"` for merged groups),
    and names visible in no panel.
    """
    radius = _MERGE_PX * view_size / DEFAULT_VIEW_SIZE
    groups: list[tuple[int, list, list[str]]] = []  # (panel_idx, [xy, ...], [name, ...])
    hidden: list[str] = []
    for c in callouts:
        for pi, (project, depth) in enumerate(panels):
            if project is None or not _visible(c["center"], project, depth):
                continue
            xy = project(c["center"])[:2]
            for g in groups:
                gx, gy = np.mean(g[1], axis=0)
                if g[0] == pi and np.hypot(xy[0] - gx, xy[1] - gy) <= radius:
                    g[1].append(xy)
                    g[2].append(c["name"])
                    break
            else:
                groups.append((pi, [xy], [c["name"]]))
            break
        else:
            hidden.append(c["name"])
    badges: list[list] = [[] for _ in panels]
    legend: list[dict] = []
    for num, (pi, xys, names) in enumerate(groups, start=1):
        badges[pi].append((num, tuple(np.mean(xys, axis=0))))
        label = names[0] if len(set(names)) == 1 else " + ".join(names)
        legend.append({"name": f"{label} x{len(names)}" if len(names) > 1 else label})
    return badges, legend, hidden


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

    Rasterizes with a numpy z-buffer (zbuffer.py): per-pixel depth test, so coplanar
    flat faces shade uniformly, with silhouette/depth-discontinuity edge lines. No
    display server or OpenGL needed. Every view is orthographic.

    `focus` is an optional `(center_xyz, size_mm)` pair overriding the default
    whole-mesh-fit framing with a fixed-size window centered on a point -- used for
    feature detail views where the feature is small relative to the whole part and
    would be imperceptible at the default whole-part framing.

    `callouts` (with `ortho=True`) is a list of `{"name": str, "center": (x, y, z)}`
    badged where the anchor is visible; the tile path (`render_multi_view`) places
    callouts across panels itself.
    """
    img, project, depth, _ = _render_panel(wp, elev, azim, width, height, focus)
    if callouts and ortho and project is not None:
        badges = [
            (i, project(c["center"])[:2])
            for i, c in enumerate(callouts, start=1)
            if _visible(c["center"], project, depth)
        ]
        _draw_callouts(img, badges)
    return img


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


def _draw_marker(img, marker, project, depth):
    """Badge `marker=(number, xyz)` at its projected position when it is visible."""
    if marker and project is not None:
        number, xyz = marker
        if _visible(xyz, project, depth):
            _draw_callouts(img, [(number, tuple(project(xyz)[:2]))])


def render_detail_view(
    wp,
    output_path,
    focus_center,
    focus_size,
    elev=25,
    azim=-60,
    view_size=DETAIL_VIEW_SIZE,
    marker=None,
):
    """Render a single high-resolution, zoomed-in view of a small feature.

    `focus_center` is `(x, y, z)` in the part's build pose and `focus_size` is
    the span (mm) of the cubic window to frame -- use roughly 2-4x the feature's
    own size so it's centered with some surrounding context, not the whole part's
    extent. Standalone file, not part of a tile: pair with a descriptive,
    feature-named `output_path` (see `run_cadquery_model.py --detail`). `marker`, an
    `(x, y, z)` anchor, gets the callout badge when the z-buffer shows it unoccluded.
    """
    img, project, depth, _ = _render_panel(
        wp, elev, azim, view_size, view_size, focus=(tuple(focus_center), focus_size)
    )
    _draw_marker(img, project, depth, marker)
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
    marker=None,
):
    """Render a high-resolution, zoomed-in cross-section through a small feature.

    Cuts `wp` at `axis`/`position` (same convention as the targeted
    `--extra-section` cuts) and frames the result on `focus_center`/`focus_size`
    (see `render_detail_view`). Returns `output_path` on success, `None` if the
    cut fails (OCC failure on a degenerate cut plane) -- the caller should skip
    writing that file and warn rather than save a meaningless blank image under a
    feature-specific name. `marker` is as in `render_detail_view`.
    """
    shape = _get_shape(wp)
    sec = _cut_half(shape, axis, position, remove_positive=_SECTION_REMOVE_POSITIVE[axis])
    if sec is None:
        return None
    elev, azim = _SECTION_CAMERA[axis]
    img, project, depth, informative = _render_panel(
        sec,
        elev,
        azim,
        view_size,
        view_size,
        focus=(tuple(focus_center), focus_size),
        cap=(axis, position),
        uncut=shape,
    )
    if marker is not None:  # sit the anchor on the cap so the occlusion test sees it
        on_cap = list(marker)
        on_cap["xyz".index(axis)] = position
        _draw_marker(img, project, depth, on_cap)
    img.save(output_path)
    return SectionPath(output_path, informative)


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
    img, _, _, informative = _render_panel(
        sec, elev, azim, view_size, view_size, cap=(axis, position), uncut=shape
    )
    img.save(output_path)
    return SectionPath(output_path, informative)


# (elev, azim) of a camera looking at a face whose outward normal is the key.
_NORMAL_CAMERA = {
    (1, 0, 0): (0, 0),
    (-1, 0, 0): (0, 180),
    (0, 1, 0): (0, 90),
    (0, -1, 0): (0, -90),
    (0, 0, 1): (90, -90),
    (0, 0, -1): (-90, -90),
}
_ISO_CAMERA = (25, -60)
_PROBE_SIZE = 300


def _feature_focus(frame):
    """(center, size_mm) framing a feature bbox with some surrounding context."""
    lo, hi = frame["bbox"]["min"], frame["bbox"]["max"]
    return tuple(frame["center"]), max(max(h - lo_ for lo_, h in zip(lo, hi, strict=True)) * 2, 6.0)


def _feature_camera(wp, frame, anchor):
    """(elev, azim): along the normal, else the opposite side, else isometric, by visibility."""
    center, size = _feature_focus(frame)
    normal = tuple(frame["normal"])
    flipped = tuple(-v for v in normal)
    for key in (normal, flipped):
        elev, azim = _NORMAL_CAMERA[key]
        _, project, depth, _ = _render_panel(
            wp, elev, azim, _PROBE_SIZE, _PROBE_SIZE, focus=(center, size)
        )
        if project is not None and _visible(anchor, project, depth):
            return elev, azim
    return _ISO_CAMERA


def render_feature_view(wp, output_path, frame, anchor, view_size=DETAIL_VIEW_SIZE):
    """Render a feature (see `feature_frame.feature_frame`) from along its normal.

    Framed on the feature bbox with the marker badge at `anchor`; the camera falls back
    to the opposite side, then to isometric, when the anchor is occluded. Returns the
    output path.
    """
    elev, azim = _feature_camera(wp, frame, anchor)
    center, size = _feature_focus(frame)
    return render_detail_view(wp, output_path, center, size, elev, azim, view_size, marker=anchor)


def feature_section_plane(frame):
    """(axis, position) of the section through a feature's axis, or None when it is flat.

    The plane contains the normal and the feature's longer in-plane axis, so its own
    normal is the shorter in-plane axis, at the bbox centre.
    """
    if frame["depth_mm"] < FLAT_DEPTH_MM:
        return None
    lo, hi = frame["bbox"]["min"], frame["bbox"]["max"]
    n = frame["axis"]
    inplane = [i for i, a in enumerate("xyz") if a != n]
    short = min(inplane, key=lambda i: hi[i] - lo[i])
    return "xyz"[short], frame["center"][short]


def render_feature_section(wp, output_path, frame, anchor, view_size=DETAIL_VIEW_SIZE):
    """Section through a feature's axis with the marker; None for a flat feature or a failed cut."""
    plane = feature_section_plane(frame)
    if plane is None:
        return None
    center, size = _feature_focus(frame)
    return render_detail_section(
        wp, output_path, plane[0], plane[1], center, size, view_size, marker=anchor
    )


def _legend_line(callouts, unlocated_names, hidden_names=None):
    """Caption legend row mapping badge numbers to names, or None if no callouts."""
    if not callouts and not unlocated_names and not hidden_names:
        return None
    parts = [f"{i} {c['name']}" for i, c in enumerate(callouts or [], start=1)]
    parts += [f"{name} (hidden)" for name in (hidden_names or [])]
    parts += [f"{name} (not located)" for name in (unlocated_names or [])]
    return "   ".join(parts)


SHEET_MAX_TILES = 4


def sheet_legend(tiles, not_shown=(), not_located=()):
    """Footer entries: "NAME (not shown)" for dropped tiles/features, "NAME (not located)"."""
    dropped = [caption for _, caption in list(tiles)[SHEET_MAX_TILES:]]
    return [f"{n} (not shown)" for n in [*not_shown, *dropped]] + [
        f"{n} (not located)" for n in not_located
    ]


def render_sheet(tiles, path, title="Preview sheet", not_shown=(), not_located=()):
    """Compose at most SHEET_MAX_TILES `(PIL image, caption)` tiles into a 2 x 2 PNG.

    Tiles beyond the cap are dropped and their captions listed, with `not_shown`, as
    "NAME (not shown)" in the footer legend; `not_located` names get "(not located)".
    Each tile is scaled to fit a DEFAULT_VIEW_SIZE square, aspect kept. Returns `path`.
    """
    tiles = list(tiles)
    shown = tiles[:SHEET_MAX_TILES]
    legend = sheet_legend(tiles, not_shown, not_located)
    size, gap, label_h, header_h = DEFAULT_VIEW_SIZE, 4, 24, 40
    footer_h = 30 if legend else 10
    w = size * 2 + gap
    rows = max(1, (len(shown) + 1) // 2)
    h = header_h + rows * (size + label_h) + (rows - 1) * gap + footer_h
    canvas = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((w // 2, 12), title, fill="black", font=_get_font(20), anchor="mt")
    for idx, (img, caption) in enumerate(shown):
        px = (idx % 2) * (size + gap)
        py = header_h + label_h + (idx // 2) * (size + label_h + gap)
        tile = img.convert("RGB")
        tile.thumbnail((size, size))
        canvas.paste(tile, (px + (size - tile.width) // 2, py + (size - tile.height) // 2))
        draw.text(
            (px + size // 2, py - 4), caption, fill="#444444", font=_get_font(14), anchor="mb"
        )
    if legend:
        draw.text(
            (w // 2, h - 8), "   ".join(legend), fill="#333333", font=_get_font(13), anchor="mb"
        )
    canvas.save(path)
    return path


def side_by_side(left, right):
    """Two square images as one image of twice the width (feature view + its section)."""
    out = Image.new("RGB", (left.width + right.width, max(left.height, right.height)), "white")
    out.paste(left, (0, 0))
    out.paste(right, (left.width, 0))
    return out


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
    (build pose) -- each gets a numbered badge + leader line on the first panel
    (orthographic panels, then isometric) where a z-buffer test shows it unoccluded;
    badges within 12 px merge ("name xN"); a callout visible nowhere is listed
    "name (hidden)". The caption legend maps badge numbers to names.

    `unlocated_names` are named features with no known position: listed in the
    legend unbadged as "name (not located)" so the tile still carries the complete
    agreed vocabulary. Neither argument changes anything when omitted.
    """
    _, triangles = _tessellate(wp)
    rendered = [
        _render_panel(wp, elev, azim, view_size, view_size)
        for elev, azim, _label, _ortho in MULTI_VIEW_PANELS
    ]
    legend_callouts, hidden = callouts, []
    if callouts:
        badges, legend_callouts, hidden = _place_callouts(
            callouts, [(r[1], r[2]) for r in rendered], view_size
        )
        for r, panel_badges in zip(rendered, badges, strict=True):
            _draw_callouts(r[0], panel_badges)
    legend_line = _legend_line(legend_callouts, unlocated_names, hidden)
    images = [(r[0], p[2]) for r, p in zip(rendered, MULTI_VIEW_PANELS, strict=True)]

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
