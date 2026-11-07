#!/usr/bin/env python3
"""Derive a feature's bounding box, normal and depth from the built solid.

Usage:
    python feature_frame.py model.py --center x,y,z [--diameter D] [--size W,H]

Prints {"located": true, "bbox": {"min", "max"}, "center", "axis", "normal", "depth_mm"}
or {"located": false} when no solid face lies near the position.
"""

import argparse
import json
import sys
from typing import cast

from section_select import _axis_index

AXES = "xyz"
MIN_WINDOW_MM = 2.0
FLAT_DEPTH_MM = 0.5  # below this a feature has no depth worth a section


def _extents(bb):
    return (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)


def _lo_hi(bb):
    return (bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmax)


def window_radius(diameter_mm=None, size_mm=None):
    """Search-window radius: the feature's own extent, never below MIN_WINDOW_MM."""
    return max(diameter_mm or 0.0, *(size_mm or [0.0]), MIN_WINDOW_MM)


def _face_axis(face):
    """(axis_idx, is_planar) a face points along, else None (non-axis-aligned or other)."""
    kind = face.geomType()
    try:
        if kind == "PLANE":
            n = face.normalAt()
            i = max(range(3), key=lambda k: abs((n.x, n.y, n.z)[k]))
            return (i, True) if abs((n.x, n.y, n.z)[i]) > 1 - 1e-3 else None
        if kind == "CYLINDER":
            idx = _axis_index(face._geomAdaptor().Cylinder().Axis().Direction())
        elif kind == "CONE":
            idx = _axis_index(face._geomAdaptor().Cone().Axis().Direction())
        else:
            return None
    except Exception:
        return None
    return None if idx is None else (idx, False)


def _host_axis(host, position):
    """Axis of the axis-aligned planar host face nearest `position` (larger area breaks ties).

    The nearest plane is the wall the feature sits in; a bigger face further away (a floor
    seen across a large window) must not outvote it.
    """
    best = None
    for face in host:
        a = _face_axis(face)
        if not (a and a[1]):
            continue
        dist = abs(face.Center().toTuple()[a[0]] - position[a[0]])
        key = (round(dist / 0.5), -face.Area())
        if best is None or key < best[0]:
            best = (key, a[0])
    return None if best is None else best[1]


def feature_frame(shape, position, diameter_mm=None, size_mm=None):
    """Frame of the feature near `position`, or None when no faces are found.

    Faces whose bbox meets a cube of radius `window_radius` around `position` are the
    candidates; those spanning more than twice that radius are the host wall and are
    excluded from the bbox. The normal axis is the host wall's (nearest planar host
    face), else the remaining faces' area-dominant axis; its sign points from the part
    centre toward the feature. `depth_mm` is the bbox extent along the normal.
    """
    r = window_radius(diameter_mm, size_mm)
    feat: list = []
    host: list = []
    for face in shape.Faces():
        lo, hi = _lo_hi(face.BoundingBox())
        if any(hi[i] < position[i] - r or lo[i] > position[i] + r for i in range(3)):
            continue
        spans = max(_extents(face.BoundingBox()))
        (host if spans > 2 * r else feat).append(face)
    if not feat:
        return None

    los, his = zip(*(_lo_hi(f.BoundingBox()) for f in feat), strict=True)
    lo = [min(v[i] for v in los) for i in range(3)]
    hi = [max(v[i] for v in his) for i in range(3)]

    idx = _host_axis(host, position)
    if idx is None:
        score = [0.0, 0.0, 0.0]
        for face in feat:
            a = _face_axis(face)
            if a:
                score[a[0]] += face.Area()
        if not any(score):
            return None
        idx = max(range(3), key=lambda k: score[k])

    pb = shape.BoundingBox()
    plo, phi = _lo_hi(pb)
    centre = (plo[idx] + phi[idx]) / 2
    sign = 1 if position[idx] >= centre else -1
    normal = [0, 0, 0]
    normal[idx] = sign
    return {
        "located": True,
        "bbox": {"min": [round(v, 3) for v in lo], "max": [round(v, 3) for v in hi]},
        "center": [round((lo[i] + hi[i]) / 2, 3) for i in range(3)],
        "axis": AXES[idx],
        "normal": normal,
        "depth_mm": round(hi[idx] - lo[idx], 3),
    }


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("script")
    parser.add_argument("--center", required=True, metavar="X,Y,Z")
    parser.add_argument("--diameter", type=float)
    parser.add_argument("--size", metavar="W,H")
    args = parser.parse_args()

    try:
        center = [float(v) for v in args.center.split(",")]
        if len(center) != 3:
            raise ValueError("--center must be 3 comma-separated values")
        size = [float(v) for v in args.size.split(",")] if args.size else None
        import cadquery as cq

        from exporters import _load_result
        from units import KEEP_OUT_KEY

        result = _load_result(args.script)
        shape: cq.Shape
        if isinstance(result, dict):
            vals = cast(list[cq.Shape], [wp.val() for k, wp in result.items() if k != KEEP_OUT_KEY])
            shape = cq.Compound.makeCompound(vals)
        else:
            shape = cast(cq.Shape, result.val())
        frame = feature_frame(shape, center, args.diameter, size)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(frame or {"located": False}))


if __name__ == "__main__":
    main()
