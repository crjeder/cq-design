#!/usr/bin/env python3
"""Derive a named feature's bbox, axis-snapped normal and depth from the built solid.

Usage:
    python feature_frame.py model.py --feature "name=usb;center=10,-25,2;diameter=5" ...
    (--feature also accepts ";size=w,h" in place of ";diameter=d")

Prints {"features": [{"name", "located", "bbox_min", "bbox_max", "center", "axis",
"sign", "depth_mm"}]}; a feature with no solid faces near its position has
"located": false and no frame fields.
"""

import argparse
import json
import sys
from typing import cast

AXES = "xyz"

MIN_WINDOW_MM = 2.0
HOST_FACTOR = 2.0  # a face spanning more than HOST_FACTOR x the window is the host wall


def parse_feature_spec(spec: str) -> dict:
    """Parse `name=<n>;center=x,y,z;diameter=<d>|size=<w>[,<h>]` into `{name, center, extent}`.

    `extent` is the feature's largest 2D dimension in mm (0 when neither key is given).
    Raises ValueError naming the problem on a malformed spec.
    """
    parts = dict(item.split("=", 1) for item in spec.split(";") if "=" in item)
    for required in ("name", "center"):
        if required not in parts:
            raise ValueError(f"missing '{required}=' in --feature spec '{spec}'")
    name = parts["name"].strip()
    if not name:
        raise ValueError(f"empty name= in --feature spec '{spec}'")
    try:
        center = tuple(float(v) for v in parts["center"].split(","))
        dims = [float(v) for v in (parts.get("diameter") or parts.get("size") or "0").split(",")]
    except ValueError as exc:
        raise ValueError(f"non-numeric center/diameter/size in --feature spec '{spec}'") from exc
    if len(center) != 3:
        raise ValueError(f"center= must be 3 comma-separated values in --feature spec '{spec}'")
    return {"name": name, "center": center, "extent": max(dims)}


def _snap(x, y, z, tol=1e-3):
    """Index of the world axis (x, y, z) is parallel to, else None."""
    comps = [abs(x), abs(y), abs(z)]
    i = max(range(3), key=lambda k: comps[k])
    return i if comps[i] > 1 - tol else None


def _face_axis(face) -> tuple[int | None, bool]:
    """(world axis index of the face's normal/axis or None, is_planar)."""
    kind = face.geomType()
    if kind == "PLANE":
        return _snap(*face.normalAt().toTuple()), True
    if kind in ("CYLINDER", "CONE"):
        surf = face._geomAdaptor()
        d = (surf.Cylinder() if kind == "CYLINDER" else surf.Cone()).Axis().Direction()
        return _snap(d.X(), d.Y(), d.Z()), False
    return None, False


def section_plane(frame: dict) -> tuple[str, float]:
    """(axis, position_mm) of the axis-aligned plane containing the frame's normal and its
    longer in-plane axis, through the bbox centre (plane normal = the shorter in-plane axis)."""
    n = AXES.index(frame["axis"])
    ext = [hi - lo for lo, hi in zip(frame["bbox_min"], frame["bbox_max"], strict=True)]
    shorter = min((i for i in range(3) if i != n), key=lambda i: ext[i])
    return AXES[shorter], frame["center"][shorter]


def derive_frame(shape, center, extent=0.0) -> dict | None:
    """Frame dict for the feature at `center` (mm), or None when no solid faces are near it.

    Window radius is `max(extent, MIN_WINDOW_MM)`. Faces spanning more than HOST_FACTOR x the
    window are the host wall: they are excluded from the bbox/depth and, when planar, set the
    normal axis (the surface the feature sits on); without a host the area-weighted axis of
    the remaining faces decides. `sign` points away from the part bbox centre.
    """
    win = max(extent, MIN_WINDOW_MM)
    lo = [c - win for c in center]
    hi = [c + win for c in center]
    kept, host_area, vote_area = [], [0.0] * 3, [0.0] * 3
    for face in shape.Faces():
        bb = face.BoundingBox()
        fmin, fmax = (bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmax)
        if any(fmin[i] > hi[i] or fmax[i] < lo[i] for i in range(3)):
            continue
        axis, planar = _face_axis(face)
        if max(fmax[i] - fmin[i] for i in range(3)) > HOST_FACTOR * 2 * win:
            if planar and axis is not None:
                host_area[axis] += face.Area()
            continue
        kept.append((fmin, fmax))
        if axis is not None:
            vote_area[axis] += face.Area()
    if not kept:
        return None
    votes = host_area if any(host_area) else vote_area
    if not any(votes):
        return None  # only free-form faces: no world axis to snap to
    idx = max(range(3), key=lambda i: votes[i])
    bmin = [min(f[0][i] for f in kept) for i in range(3)]
    bmax = [max(f[1][i] for f in kept) for i in range(3)]
    sb = shape.BoundingBox()
    mid = ((sb.xmin + sb.xmax) / 2, (sb.ymin + sb.ymax) / 2, (sb.zmin + sb.zmax) / 2)[idx]
    return {
        "bbox_min": [round(v, 3) for v in bmin],
        "bbox_max": [round(v, 3) for v in bmax],
        "center": [round((a + b) / 2, 3) for a, b in zip(bmin, bmax, strict=True)],
        "axis": AXES[idx],
        "sign": 1 if center[idx] >= mid else -1,
        "depth_mm": round(bmax[idx] - bmin[idx], 3),
    }


def frames_for(shape, specs: list[dict]) -> list[dict]:
    """`[{name, located, ...frame}]` for parsed feature specs, in order."""
    out = []
    for s in specs:
        frame = derive_frame(shape, s["center"], s["extent"])
        out.append({"name": s["name"], "located": frame is not None, **(frame or {})})
    return out


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("script")
    parser.add_argument("--feature", action="append", default=[], metavar="SPEC")
    args = parser.parse_args()
    try:
        import cadquery as cq

        from exporters import _load_result
        from units import KEEP_OUT_KEY

        specs = [parse_feature_spec(s) for s in args.feature]
        result = _load_result(args.script)
        shape: cq.Shape
        if isinstance(result, dict):
            vals = cast(list[cq.Shape], [wp.val() for k, wp in result.items() if k != KEEP_OUT_KEY])
            shape = cq.Compound.makeCompound(vals)
        else:
            shape = cast(cq.Shape, result.val())
        features = frames_for(shape, specs)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"features": features}))


if __name__ == "__main__":
    main()
