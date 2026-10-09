"""Headless z-buffered triangle rasterizer (numpy only, no OpenGL).

Orthographic camera with matplotlib's `view_init(elev, azim)` convention, so the
compass-labelled preview panels keep their meaning: the camera sits in direction
(cos el cos az, cos el sin az, sin el) from the target, screen-right is
(-sin az, cos az, 0) and screen-up is +Z (tilting toward +Y for a top-down view).
"""

import numpy as np

_SSAA = 2


def camera_axes(elev, azim):
    """Return (toward_camera, right, up) unit vectors for a view."""
    el, az = np.radians(elev), np.radians(azim)
    c = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    r = np.array([-np.sin(az), np.cos(az), 0.0])
    return c, r, np.cross(c, r)


def make_camera(verts, elev, azim, width, height, focus=None):
    """Build `project(xyz) -> (px, py, depth)` mapping mm to pixel coords.

    `focus=(center_xyz, size_mm)` frames a fixed window on a point; otherwise the
    projected bounding box of `verts` is fitted to 90% of the canvas.
    """
    c, r, u = camera_axes(elev, azim)
    side = min(width, height)
    if focus is not None:
        center, size = focus
        cx, cy = float(np.dot(center, r)), float(np.dot(center, u))
        scale = side / (2 * max(float(size), 1.0) * 0.6)
    else:
        sx, sy = verts @ r, verts @ u
        cx, cy = (sx.max() + sx.min()) / 2, (sy.max() + sy.min()) / 2
        scale = 0.9 * side / max(sx.max() - sx.min(), sy.max() - sy.min(), 1e-6)

    def project(xyz):
        p = np.asarray(xyz, dtype=float)
        return (
            width / 2 + (p @ r - cx) * scale,
            height / 2 - (p @ u - cy) * scale,
            p @ c,
        )

    return project


def rasterize(triangles, colors, project, width, height, bg):
    """Flat-shaded z-buffered render. Returns an (height, width, 3) uint8 array.

    `triangles` is (n, 3, 3) in mm, `colors` (n, 3) floats in 0..1, `bg` an RGB
    uint8 triple. Rendered at _SSAA x resolution and box-downsampled.
    """
    w, h = width * _SSAA, height * _SSAA
    img = np.empty((h, w, 3), dtype=float)
    img[:] = np.asarray(bg, dtype=float) / 255.0
    zbuf = np.full((h, w), -np.inf)

    px, py, pz = project(triangles.reshape(-1, 3))
    px = px.reshape(-1, 3) * _SSAA
    py = py.reshape(-1, 3) * _SSAA
    pz = pz.reshape(-1, 3)

    for i in range(len(px)):
        x, y, z = px[i], py[i], pz[i]
        denom = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(denom) < 1e-12:
            continue
        x0, x1 = max(int(np.floor(x.min())), 0), min(int(np.ceil(x.max())) + 1, w)
        y0, y1 = max(int(np.floor(y.min())), 0), min(int(np.ceil(y.max())) + 1, h)
        if x0 >= x1 or y0 >= y1:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / denom
        l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / denom
        l2 = 1.0 - l0 - l1
        depth = l0 * z[0] + l1 * z[1] + l2 * z[2]
        sl = (slice(y0, y1), slice(x0, x1))
        hit = (l0 >= 0) & (l1 >= 0) & (l2 >= 0) & (depth > zbuf[sl])
        zbuf[sl][hit] = depth[hit]
        img[sl][hit] = colors[i]

    small = img.reshape(height, _SSAA, width, _SSAA, 3).mean(axis=(1, 3))
    return (np.clip(small, 0, 1) * 255 + 0.5).astype(np.uint8)
