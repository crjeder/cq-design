#!/usr/bin/env python3
"""Pick axis-aligned cross-section planes that show a part's bores and bosses.

Usage:
    python section_select.py model.py [--max 3] [--reserve x=10]...

Prints {"sections": [{"axis", "position_mm", "features"}], "extra_section_args": ["x=10"]}.
"""

import argparse
import json
import math
import sys
import time
from typing import cast

AXES = "xyz"
MIN_RADIUS_MM = 0.5
MIN_COVERAGE = 0.5  # face area / full-cylinder area; drops fillets, keeps seam-split halves
DEDUPE_MM = 0.5
SLICES_PER_AXIS = 15
SLICE_BUDGET_S = 5.0
MIN_SLICE_SCORE = 0.5  # below this a slice shows nothing a bbox-centre cut would not
MAX_LOOPS_SCORED = 6


def _axis_index(direction, tol=1e-3):
    """Index of the world axis `direction` is parallel to, else None."""
    comps = [abs(direction.X()), abs(direction.Y()), abs(direction.Z())]
    i = max(range(3), key=lambda k: comps[k])
    return i if comps[i] > 1 - tol else None


def _face_feature(face):
    """(axis_idx, center_xyz, radius, lo, hi, coverage) for a cylinder/cone face, else None."""
    kind = face.geomType()
    if kind not in ("CYLINDER", "CONE"):
        return None
    surf = face._geomAdaptor()
    if kind == "CYLINDER":
        prim = surf.Cylinder()
        radius = prim.Radius()
    else:
        prim = surf.Cone()
        radius = None
    ax = prim.Axis()
    idx = _axis_index(ax.Direction())
    if idx is None:
        return None
    loc = ax.Location()
    center = (loc.X(), loc.Y(), loc.Z())
    bb = face.BoundingBox()
    lo = (bb.xmin, bb.ymin, bb.zmin)[idx]
    hi = (bb.xmax, bb.ymax, bb.zmax)[idx]
    if radius is None:  # cone: widest perpendicular half-extent
        ext = [(bb.xmax - bb.xmin), (bb.ymax - bb.ymin), (bb.zmax - bb.zmin)]
        radius = max(e for i, e in enumerate(ext) if i != idx) / 2
        coverage = 1.0
    else:
        length = hi - lo
        coverage = face.Area() / (2 * math.pi * radius * length) if length > 0 else 0.0
    return idx, center, radius, lo, hi, coverage


def detect_features(shape):
    """Axis-aligned bores/bosses as dicts, coaxial faces merged into one stepped feature."""
    groups: dict[tuple[int, float, float], dict] = {}
    for face in shape.Faces():
        f = _face_feature(face)
        if f is None:
            continue
        idx, center, radius, lo, hi, coverage = f
        if coverage < MIN_COVERAGE or radius < MIN_RADIUS_MM:
            continue
        perp = [center[i] for i in range(3) if i != idx]
        key = (idx, round(perp[0], 1), round(perp[1], 1))
        g = groups.setdefault(key, {"perp": perp, "radii": set(), "lo": lo, "hi": hi})
        g["radii"].add(round(radius, 2))
        g["lo"], g["hi"] = min(g["lo"], lo), max(g["hi"], hi)
    feats = []
    for (idx, _, _), g in sorted(groups.items()):
        feats.append(
            {
                "kind": "stepped" if len(g["radii"]) > 1 else "bore",
                "axis": AXES[idx],
                "center": [round(v, 3) for v in g["perp"]],
                "radius_mm": max(g["radii"]),
                "length_mm": round(g["hi"] - g["lo"], 3),
            }
        )
    return feats


def _weight(feat):
    return feat["radius_mm"] * feat["length_mm"] * (1.5 if feat["kind"] == "stepped" else 1.0)


def _plane_coords(feat):
    """[(plane_axis, position)] of the two planes containing the feature's axis."""
    others = [a for a in AXES if a != feat["axis"]]
    return list(zip(others, feat["center"], strict=True))


def _shows(feat, axis, pos):
    for a, c in _plane_coords(feat):
        if a == axis:
            return abs(pos - c) < feat["radius_mm"]
    return False  # plane normal to the feature's own axis


def select_sections(shape, max_cuts=3, reserved=()):
    """Return up to `max_cuts` [{axis, position_mm, features}] through feature axes.

    `reserved` is [(axis, pos)] of cuts the caller already has; features they show
    are treated as covered and new cuts within DEDUPE_MM of them are dropped.
    """
    feats = detect_features(shape)
    remaining = [f for f in feats if not any(_shows(f, a, p) for a, p in reserved)]
    cands = sorted({(a, p) for f in remaining for a, p in _plane_coords(f)})
    cands = [
        (a, p)
        for a, p in cands
        if not any(a == ra and abs(p - rp) < DEDUPE_MM for ra, rp in reserved)
    ]
    out = []
    for _ in range(max_cuts):
        best = None
        for a, p in cands:
            gain = sum(_weight(f) for f in remaining if _shows(f, a, p))
            key = (-gain, AXES.index(a), p)
            if gain > 0 and (best is None or key < best[0]):
                best = (key, a, p)
        if best is None:
            break
        _, a, p = best
        shown = [f for f in remaining if _shows(f, a, p)]
        remaining = [f for f in remaining if f not in shown]
        cands = [(ca, cp) for ca, cp in cands if not (ca == a and abs(cp - p) < DEDUPE_MM)]
        out.append({"axis": a, "position_mm": round(p, 3), "features": shown})
    return out


def _slice_stats(shape, axis, pos, bb):
    """(area, loops, void_fraction) of the shape's section at `axis`=`pos`, None if empty.

    loops counts every boundary but the outermost (holes and island outlines); void is
    the share of the section's own bbox that is empty.
    """
    import cadquery as cq

    n = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    base = [(bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2]
    base["xyz".index(axis)] = pos
    span = max(bb.xlen, bb.ylen, bb.zlen) * 2
    faces = shape.intersect(cq.Face.makePlane(span, span, tuple(base), n)).Faces()
    area = sum(f.Area() for f in faces)
    if not faces or area <= 0:
        return None
    loops = sum(len(f.Wires()) for f in faces) - 1
    sb = cq.Compound.makeCompound(faces).BoundingBox()
    ext = sorted([sb.xlen, sb.ylen, sb.zlen])[1:]  # the two in-plane extents
    return area, loops, max(0.0, 1.0 - area / max(ext[0] * ext[1], 1e-9))


def score_slices(shape, max_cuts=2, reserved=(), budget_s=SLICE_BUDGET_S):
    """Up to `max_cuts` [{axis, position_mm, score}] from slice analysis; [] past the time budget.

    Samples SLICES_PER_AXIS planes per axis; score = min(loops, 6) + 2 x void fraction +
    area change vs the neighbouring slices (relative to the axis' largest area). Takes the
    best slice per axis, drops any within DEDUPE_MM of a `reserved` cut or scoring below
    MIN_SLICE_SCORE, then the best `max_cuts`.
    """
    start = time.monotonic()
    bb = shape.BoundingBox()
    best = []
    for axis in AXES:
        lo = getattr(bb, axis + "min")
        step = getattr(bb, axis + "len") / (SLICES_PER_AXIS + 1)
        poses = [lo + step * (i + 1) for i in range(SLICES_PER_AXIS)]
        stats = []
        for p in poses:
            if time.monotonic() - start > budget_s:
                return []
            stats.append(_slice_stats(shape, axis, p, bb))
        top = max((st[0] for st in stats if st), default=0.0)
        cands = []
        for i, (p, st) in enumerate(zip(poses, stats, strict=True)):
            if st is None or top <= 0:
                continue
            nbrs = [stats[j][0] for j in (i - 1, i + 1) if 0 <= j < len(stats) and stats[j]]
            change = sum(abs(st[0] - a) for a in nbrs) / (len(nbrs) or 1) / top
            score = min(st[1], MAX_LOOPS_SCORED) + 2 * st[2] + change
            if score >= MIN_SLICE_SCORE and not any(
                axis == ra and abs(p - rp) < DEDUPE_MM for ra, rp in reserved
            ):
                cands.append((score, axis, p))
        if cands:
            best.append(max(cands, key=lambda c: (c[0], -abs(c[2] - (lo + step * 8)))))
    best.sort(key=lambda c: -c[0])
    return [
        {"axis": a, "position_mm": round(p, 3), "score": round(s, 3)} for s, a, p in best[:max_cuts]
    ]


def _parse_reserve(spec):
    axis, _, val = spec.partition("=")
    axis = axis.strip().lower()
    if axis not in AXES or not val:
        raise ValueError(f"--reserve '{spec}': expected AXIS=MM with AXIS one of x/y/z")
    return axis, float(val)


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("script")
    parser.add_argument("--max", type=int, default=3)
    parser.add_argument("--reserve", action="append", default=[], metavar="AXIS=MM")
    args = parser.parse_args()

    try:
        reserved = [_parse_reserve(s) for s in args.reserve]
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
        sections = select_sections(shape, args.max, reserved)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(
        json.dumps(
            {
                "sections": sections,
                "extra_section_args": [f"{s['axis']}={s['position_mm']:g}" for s in sections],
            }
        )
    )


if __name__ == "__main__":
    main()
