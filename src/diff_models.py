"""Diff two watertight STL files: JSON summary plus an optional diff preview PNG.

Common geometry is gray, geometry only in A red, geometry only in B green.
Inputs are assumed to share a frame; there is no alignment.
"""

import argparse
import json
import sys
from typing import Any

import numpy as np
import trimesh
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from mesh_io import load_mesh

_COLORS = {"common": (0.6, 0.6, 0.6), "only_a": (0.85, 0.15, 0.15), "only_b": (0.15, 0.7, 0.25)}


def _err(kind, message, hint):
    return {"type": kind, "message": message, "hint": hint}


def _boolean(op, a, b):
    """Boolean of two meshes; None when the result is empty."""
    r = trimesh.boolean.boolean_manifold([a, b], operation=op)
    return r if len(r.faces) else None


def _vol(m):
    return 0.0 if m is None else abs(float(m.volume))


def _render_png(parts, path):
    fig = Figure(figsize=(6, 6), dpi=120)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(projection="3d")
    light = np.array([1.0, 1.0, 2.0]) / np.linalg.norm([1.0, 1.0, 2.0])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for name, m in parts.items():
        if m is None:
            continue
        tris = m.triangles
        shade = 0.4 + 0.6 * np.clip(m.face_normals @ light, 0, 1)
        colors = np.clip(np.outer(shade, _COLORS[name]), 0, 1)
        ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, linewidths=0))
        lo, hi = np.minimum(lo, m.bounds[0]), np.maximum(hi, m.bounds[1])
    c, r = (lo + hi) / 2, float((hi - lo).max()) / 2 or 1.0
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=25, azim=-60)
    ax.set_axis_off()
    fig.savefig(path)


def _outside_volume(parts, region):
    """Volume of the only-A and only-B material outside the region box."""
    lo, hi = np.array(region[:3], float), np.array(region[3:], float)
    box = trimesh.creation.box(bounds=[lo, hi])
    return sum(_vol(_boolean("difference", m, box)) if m is not None else 0.0 for m in parts)


def _region_fraction(a, region):
    lo = np.maximum(a.bounds[0], region[:3])
    hi = np.minimum(a.bounds[1], region[3:])
    return float(np.prod(np.clip(hi - lo, 0, None)) / np.prod(a.bounds[1] - a.bounds[0]))


def diff_models(
    path_a, path_b, png=None, tol=1e-6, region=None, expect_volume=None, outside_tol=0.005
):
    """Return the JSON-contract dict for the diff of two STL files.

    region = (xmin, ymin, zmin, xmax, ymax, zmax); expect_volume = (lo, hi) for only_b - only_a.
    """
    out: dict[str, Any] = {
        "success": False,
        "errors": [],
        "volume_a": None,
        "volume_b": None,
        "only_a_volume": None,
        "only_b_volume": None,
        "common_volume": None,
        "bbox_delta": None,
        "identical": None,
        "outside_volume": None,
        "changed_bbox": None,
        "volume_delta": None,
        "localized": None,
        "volume_in_range": None,
        "region_fraction": None,
        "png": None,
    }
    meshes = []
    for p in (path_a, path_b):
        try:
            m = load_mesh(p)
        except ValueError as e:
            out["errors"].append(_err("load_failed", f"{p}: {e}", "Pass a valid STL file"))
            return out
        if not m.is_watertight:
            out["errors"].append(
                _err(
                    "not_watertight",
                    f"{p} is not watertight",
                    "Diff needs closed meshes; repair or re-export the STL",
                )
            )
            return out
        meshes.append(m)
    a, b = meshes
    try:
        parts = {
            "common": _boolean("intersection", a, b),
            "only_a": _boolean("difference", a, b),
            "only_b": _boolean("difference", b, a),
        }
    except Exception as e:
        out["errors"].append(
            _err("boolean_failed", str(e), "Meshes may be degenerate or self-intersecting")
        )
        return out
    out.update(
        volume_a=abs(float(a.volume)),
        volume_b=abs(float(b.volume)),
        only_a_volume=_vol(parts["only_a"]),
        only_b_volume=_vol(parts["only_b"]),
        common_volume=_vol(parts["common"]),
        bbox_delta=(b.bounds - a.bounds).round(6).tolist(),
    )
    total = out["volume_a"] + out["volume_b"]
    out["identical"] = out["only_a_volume"] + out["only_b_volume"] <= tol * total
    out["volume_delta"] = out["only_b_volume"] - out["only_a_volume"]
    changed = [m for m in (parts["only_a"], parts["only_b"]) if m is not None]
    if changed:
        bounds = np.array([m.bounds for m in changed])
        out["changed_bbox"] = [bounds[:, 0].min(axis=0).tolist(), bounds[:, 1].max(axis=0).tolist()]
    if region is not None:
        try:
            out["outside_volume"] = _outside_volume(changed, region)
        except Exception as e:
            out["errors"].append(_err("boolean_failed", str(e), "Region check failed"))
            return out
        out["localized"] = out["outside_volume"] <= outside_tol * out["volume_a"]
        out["region_fraction"] = _region_fraction(a, np.array(region, float))
    if expect_volume is not None:
        out["volume_in_range"] = expect_volume[0] <= out["volume_delta"] <= expect_volume[1]
    if png:
        _render_png(parts, png)
        out["png"] = png
    out["success"] = True
    return out


def _floats(n):
    def parse(s):
        v = [float(x) for x in s.split(",")]
        if len(v) != n:
            raise argparse.ArgumentTypeError(f"expected {n} comma-separated numbers")
        return v

    return parse


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--png")
    ap.add_argument(
        "--tol", type=float, default=1e-6, help="relative volume tolerance for 'identical'"
    )
    ap.add_argument("--region", type=_floats(6), help="xmin,ymin,zmin,xmax,ymax,zmax of the edit")
    ap.add_argument("--expect-volume", type=_floats(2), help="LO,HI for only_b - only_a volume")
    ap.add_argument("--outside-tol", type=float, default=0.005, help="outside volume / volume_a")
    args = ap.parse_args()
    res = diff_models(
        args.a, args.b, args.png, args.tol, args.region, args.expect_volume, args.outside_tol
    )
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["success"] else 1)


if __name__ == "__main__":
    main()
