#!/usr/bin/env python3
"""Render the name-labeled five-view reference image of a part.

Usage:
    python3 render_labeled.py preview/design.stl preview/design.features.json \
        [out.png] [--name holder] [--plan BUILD_PLAN.json]

Reads the designed-pose STL and the feature record written by `export_design_stl.py`
and draws South / above / below / isometric / West views with a coloured name label,
leader line and anchor dot per feature, a legend and a footer. Anchors come from each
feature's recorded geometry change and the z-buffer (a feature is labeled only where it
is visible); label boxes are placed outward from the anchor and de-overlapped, so no
position is authored by hand. Prints one JSON object `{success, png, labeled, hidden,
errors}`; exit 0 on success, 1 on failure.
"""

import argparse
import json
import os
import sys
from typing import cast

import numpy as np
import trimesh
from PIL import Image, ImageDraw

import zbuffer
from preview import _BG_COLOR, _EDGE_RGB, _get_font

WIDTH = 1800
GUTTER = 20
FULL_W = WIDTH - 2 * GUTTER
HALF_W = (FULL_W - GUTTER) // 2
TITLE_H = 24
MARGIN = 70  # px kept free around the part for labels
GROW_MM = 0.1  # slack on a feature's recorded bbox when collecting its faces
VISIBLE_TOL = 0.01
PAD = 4

# (key, title, elev, azim, (w, h)): compass stations as in preview.MULTI_VIEW_PANELS.
PANELS = [
    ("south", "Viewed from South", 0, -90, (FULL_W, 300)),
    ("above", "Viewed from above", 90, -90, (FULL_W, 380)),
    ("below", "Viewed from below (inner faces, Y flipped)", -90, -90, (FULL_W, 380)),
    ("iso", "Isometric", 25, -60, (FULL_W, 650)),
    ("west", "Viewed from West", 0, 180, (HALF_W, 450)),
]

_BASE = np.array([0.36, 0.53, 0.82])

PALETTE = [
    "#1f77b4",
    "#17becf",
    "#d62728",
    "#e377c2",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#8c564b",
    "#c49c00",
    "#006d77",
    "#7f7f7f",
    "#7f3c8d",
]


def _bg() -> tuple[int, int, int]:
    r, g, b = (int(_BG_COLOR[i : i + 2], 16) for i in (1, 3, 5))
    return r, g, b


def _camera(verts, elev, azim, w, h):
    """Orthographic `project(xyz) -> (px, py, depth)` fitting the part into (w, h) with MARGIN."""
    c, r, u = zbuffer.camera_axes(elev, azim)
    sx, sy = verts @ r, verts @ u
    scale = min((w - 2 * MARGIN) / max(np.ptp(sx), 1e-6), (h - 2 * MARGIN) / max(np.ptp(sy), 1e-6))
    cx, cy = (sx.max() + sx.min()) / 2, (sy.max() + sy.min()) / 2

    def project(xyz):
        p = np.asarray(xyz, dtype=float)
        return w / 2 + (p @ r - cx) * scale, h / 2 - (p @ u - cy) * scale, p @ c

    return project, c


def _anchor(feat, cen, nrm, c, project, depth):
    """Pixel (x, y) on the feature: first of its instances (largest first) that is visible."""
    for part in feat.get("parts") or [feat]:
        hit = _part_anchor(part, cen, nrm, c, project, depth)
        if hit is not None:
            return hit
    return None


def _part_anchor(part, cen, nrm, c, project, depth):
    """Visible face centroid nearest `part`'s centroid among faces inside its bbox, or None."""
    lo = np.array(part["bbox"][0::2]) - GROW_MM
    hi = np.array(part["bbox"][1::2]) + GROW_MM
    idx = np.flatnonzero(((cen >= lo) & (cen <= hi)).all(axis=1) & (nrm @ c > 1e-6))
    if not len(idx):
        return None
    px, py, pz = project(cen[idx])
    ix, iy = px.astype(int), py.astype(int)
    h, w = depth.shape
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    covered = np.isfinite(depth)
    tol = max(VISIBLE_TOL * float(np.ptp(depth[covered])), 1e-3) if covered.any() else 1e-3
    ok[ok] = pz[ok] >= depth[iy[ok], ix[ok]] - tol
    if not ok.any():
        return None
    idx = idx[ok]
    best = idx[np.argmin(np.linalg.norm(cen[idx] - np.array(part["centroid"]), axis=1))]
    x, y, _ = project(cen[best])
    return float(x), float(y)


def _place(anchor, size, placed, panel_wh):
    """First free `(x0, y0, x1, y1)` label box outward from `anchor`, or None (no room)."""
    bw, bh = size
    w, h = panel_wh
    up = -1 if anchor[1] < h / 2 else 1
    for dist in (40, 75, 110, 145, 180):
        for sign in (up, -up):
            for dx in (0, 0.6 * bw, -0.6 * bw, 1.2 * bw, -1.2 * bw):
                x0 = anchor[0] + dx - bw / 2
                y0 = anchor[1] + sign * dist - bh / 2
                box = (x0, y0, x0 + bw, y0 + bh)
                if box[0] < 0 or box[1] < 0 or box[2] > w or box[3] > h:
                    continue
                if all(
                    box[2] + PAD <= b[0]
                    or b[2] + PAD <= box[0]
                    or box[3] + PAD <= b[1]
                    or b[3] + PAD <= box[1]
                    for b in placed
                ):
                    return box
    return None


def _draw_view(tri, cen, nrm, feats, spec, font):
    """One panel image with labels; returns `(image, set of labeled feature indexes)`."""
    _, _, elev, azim, (w, h) = spec
    project, c = _camera(tri.reshape(-1, 3), elev, azim, w, h)
    _, r, u = zbuffer.camera_axes(elev, azim)
    light = c + 0.5 * u - 0.4 * r  # camera-relative so every view is lit, not just the top
    colors = _BASE * (0.45 + 0.55 * np.clip(nrm @ (light / np.linalg.norm(light)), 0, 1))[:, None]
    arr, depth = zbuffer.rasterize_with_depth(tri, colors, project, w, h, _bg())
    arr[zbuffer.edge_mask(depth)] = _EDGE_RGB
    img = Image.fromarray(arr, "RGB")
    draw = ImageDraw.Draw(img)
    placed: list[tuple[float, float, float, float]] = []
    dots: list[tuple[float, float, float, float]] = []
    labeled: set[int] = set()
    for i, feat in enumerate(feats):
        anchor = _anchor(feat, cen, nrm, c, project, depth)
        if anchor is None:
            continue
        tb = draw.textbbox((0, 0), feat["name"], font=font, anchor="lt")
        size = (tb[2] - tb[0] + 2 * PAD + 4, tb[3] - tb[1] + 2 * PAD + 4)
        box = _place(anchor, size, placed + dots, (w, h))
        if box is None:
            continue
        placed.append(box)
        dots.append((anchor[0] - 6, anchor[1] - 6, anchor[0] + 6, anchor[1] + 6))
        labeled.add(i)
        col = PALETTE[i % len(PALETTE)]
        end = (min(max(anchor[0], box[0]), box[2]), min(max(anchor[1], box[1]), box[3]))
        draw.line([anchor, end], fill=col, width=2)
        draw.rounded_rectangle(box, radius=4, fill=col)
        draw.text(
            ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2),
            feat["name"],
            fill="white",
            font=font,
            anchor="mm",
        )
        draw.ellipse(
            [anchor[0] - 5, anchor[1] - 5, anchor[0] + 5, anchor[1] + 5],
            fill=col,
            outline="white",
            width=1,
        )
    return img, labeled


def _describe(feat) -> str:
    """Legend text: the plan description when known, else `operation, W x D x H mm`."""
    if feat.get("description"):
        return feat["description"]
    b = feat["bbox"]
    dims = " x ".join(f"{b[i + 1] - b[i]:.3g}" for i in (0, 2, 4))
    return f"{feat['operation']}, {dims} mm"


def _fit(draw, text, font, width):
    """`text` shortened with '...' to fit `width` px."""
    while draw.textlength(text, font=font) > width and len(text) > 4:
        text = text[:-4] + "..."
    return text


def _draw_legend(draw, box, feats, hidden, fonts):
    """Legend: one row per feature (colour swatch + name, description)."""
    x0, y0, x1, _ = box
    draw.text((x0, y0), "Features", fill="black", font=fonts[1], anchor="lt")
    if not feats:
        draw.text((x0, y0 + 34), "no named features", fill="#555555", font=fonts[0], anchor="lt")
        return
    name_w = max(draw.textlength(f["name"], font=fonts[0]) for f in feats) + 30
    for i, feat in enumerate(feats):
        y = y0 + 36 + i * 30
        name = feat["name"]
        tb = draw.textbbox((x0, y), name, font=fonts[0], anchor="lt")
        draw.rounded_rectangle(
            (tb[0] - PAD, tb[1] - PAD, tb[2] + PAD, tb[3] + PAD),
            radius=4,
            fill=PALETTE[i % len(PALETTE)],
        )
        draw.text((x0, y), name, fill="white", font=fonts[0], anchor="lt")
        text = _describe(feat) + (" (hidden)" if i in hidden else "")
        left = x0 + name_w
        draw.text(
            (left, y),
            _fit(draw, text, fonts[0], x1 - left),
            fill="#222222",
            font=fonts[0],
            anchor="lt",
        )


def _plan_interfaces(plan_path):
    """`{name: interface}` for every named interface in a BUILD_PLAN.json (empty if unreadable)."""
    try:
        with open(plan_path) as f:
            plan = json.load(f)
    except (OSError, ValueError):
        return {}
    return {
        i["name"]: i
        for part in plan.get("parts", [])
        for i in part.get("interfaces", [])
        if i.get("name")
    }


def build_vocabulary(features, interfaces):
    """Stage features with plan descriptions; positioned plan interfaces only if there are none."""
    out = []
    for f in features:
        itf = interfaces.get(f["name"], {})
        out.append({**f, "description": itf.get("description")})
    for name, itf in interfaces.items():
        p = itf.get("position_mm")
        if not features and p:
            bbox = [v for c in p for v in (c - 1.0, c + 1.0)]
            out.append(
                {
                    "name": name,
                    "operation": "interface",
                    "bbox": bbox,
                    "centroid": list(p),
                    "volume_mm3": 0.0,
                    "description": itf.get("description"),
                }
            )
    return out


def render_labeled(stl, features_path, out_png, name="design", plan=None):
    """Write the labeled five-view PNG; return `{labeled, hidden}` feature-name lists."""
    mesh = cast(trimesh.Trimesh, trimesh.load(stl, force="mesh"))
    tri = np.asarray(mesh.triangles, dtype=np.float64)
    nrm = np.asarray(mesh.face_normals, dtype=np.float64)
    cen = tri.mean(axis=1)
    with open(features_path) as f:
        features = json.load(f).get("features", [])
    feats = build_vocabulary(features, _plan_interfaces(plan) if plan else {})
    fonts = (_get_font(15), _get_font(20), _get_font(13))

    heights = {"south": 300, "above": 380, "below": 380, "iso": 650}
    legend_h = max(450, 36 + 30 * max(len(feats), 1) + 20)
    total_h = 60 + sum(TITLE_H + h + GUTTER for h in heights.values()) + TITLE_H + legend_h + 50
    canvas = Image.new("RGB", (WIDTH, total_h), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (WIDTH / 2, 28),
        f"{name.replace('_', ' ').title()} - feature reference",
        fill="black",
        font=fonts[1],
        anchor="mm",
    )

    labeled_any: set[int] = set()
    y = 60
    for spec in PANELS:
        key, title, _, _, (w, h) = spec
        if key == "west":
            h = legend_h
            spec = (key, title, spec[2], spec[3], (w, h))
        img, labeled = _draw_view(tri, cen, nrm, feats, spec, fonts[0])
        labeled_any |= labeled
        x = GUTTER
        draw.text((x + w / 2, y + TITLE_H - 4), title, fill="#444444", font=fonts[2], anchor="mb")
        canvas.paste(img, (x, y + TITLE_H))
        draw.rectangle((x, y + TITLE_H, x + w - 1, y + TITLE_H + h - 1), outline="black")
        if key == "west":
            hidden = {i for i in range(len(feats)) if i not in labeled_any}
            _draw_legend(
                draw,
                (x + w + GUTTER, y + TITLE_H, WIDTH - GUTTER, y + TITLE_H + h),
                feats,
                hidden,
                fonts,
            )
        y += TITLE_H + h + GUTTER

    b = mesh.bounds[1] - mesh.bounds[0]
    draw.text(
        (WIDTH / 2, total_h - 22),
        f"Bounding box: {b[0]:.1f} x {b[1]:.1f} x {b[2]:.1f} mm  |  "
        f"Triangles: {len(mesh.faces)}  |  designed pose",
        fill="#555555",
        font=fonts[0],
        anchor="mm",
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    canvas.save(out_png)
    return {
        "labeled": [f["name"] for i, f in enumerate(feats) if i in labeled_any],
        "hidden": [f["name"] for i, f in enumerate(feats) if i not in labeled_any],
    }


def main() -> None:
    """CLI entry point."""
    p = argparse.ArgumentParser(description="Render the name-labeled five-view preview")
    p.add_argument("stl")
    p.add_argument("features")
    p.add_argument("out", nargs="?", default=None)
    p.add_argument("--name", default="design", help="part name for the title and default file name")
    p.add_argument("--plan", default=None, help="BUILD_PLAN.json for legend descriptions")
    a = p.parse_args()
    out = a.out or os.path.join(os.path.dirname(a.stl) or ".", f"{a.name}_preview_labeled.png")
    try:
        res = render_labeled(a.stl, a.features, out, a.name, a.plan)
    except Exception as exc:  # report through the JSON contract, not a traceback
        print(
            json.dumps(
                {
                    "success": False,
                    "png": None,
                    "labeled": [],
                    "hidden": [],
                    "errors": [{"type": "render_error", "message": str(exc), "hint": ""}],
                }
            )
        )
        sys.exit(1)
    print(json.dumps({"success": True, "png": out, **res, "errors": []}))


if __name__ == "__main__":
    main()
