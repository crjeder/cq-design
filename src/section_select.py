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


N_SLICES = 15
MIN_SLICE_SCORE = 1.2  # a lone small hole scores ~1 and is already shown by its bore cut
SLICE_TIME_CAP_S = 5.0


def _slice_metrics(shape, axis, pos, span):
    """(area, inner_loops, void_fraction) of the section at `axis`=`pos`; None if empty.

    Void fraction is measured per section face against its own bounding box, so a
    plain rectangle scores 0 and a U profile or hollow ring scores high.
    """
    import cadquery as cq

    normal = cq.Vector(*(1 if a == axis else 0 for a in AXES))
    centre = cq.Vector(*(pos if a == axis else 0 for a in AXES))
    faces = shape.intersect(cq.Face.makePlane(span, span, centre, normal)).Faces()
    if not faces:
        return None
    area = sum(f.Area() for f in faces)
    boxes = 0.0
    for f in faces:
        bb = f.BoundingBox()
        ext = sorted([bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin])
        boxes += ext[1] * ext[2]
    loops = sum(len(f.innerWires()) for f in faces)
    return area, loops, max(0.0, 1.0 - area / boxes) if boxes > 0 else 0.0


def score_slices(shape, reserved=(), max_cuts=2, time_cap_s=SLICE_TIME_CAP_S):
    """Up to `max_cuts` [{axis, position_mm, score}] from N_SLICES planes per axis.

    Score = inner loops + 2 x void fraction + area change vs neighbouring slices. The
    best slice per axis competes; cuts within DEDUPE_MM of a `reserved` cut are dropped
    and scores below MIN_SLICE_SCORE are ignored. Returns what was scored when
    `time_cap_s` runs out (possibly []), so callers keep their bbox-centre fallback.
    """
    import time

    bb = shape.BoundingBox()
    lows, highs = (bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmax)
    span = 4 * max(h - lo for lo, h in zip(lows, highs, strict=True))
    start = time.monotonic()
    best: list[tuple[float, str, float]] = []
    for i, axis in enumerate(AXES):
        lo, hi = lows[i], highs[i]
        positions = [lo + (hi - lo) * (k + 1) / (N_SLICES + 1) for k in range(N_SLICES)]
        metrics = []
        for pos in positions:
            if time.monotonic() - start > time_cap_s:
                return _top_slices(best, max_cuts)
            metrics.append(_slice_metrics(shape, axis, pos, span))
        top = max((m[0] for m in metrics if m), default=0.0)
        scored = []
        for k, (pos, m) in enumerate(zip(positions, metrics, strict=True)):
            if m is None or top <= 0:
                continue
            nbrs = [metrics[j][0] for j in (k - 1, k + 1) if 0 <= j < N_SLICES and metrics[j]]
            change = abs(m[0] - sum(nbrs) / len(nbrs)) / top if nbrs else 0.0
            score = m[1] + 2.0 * m[2] + change
            if not any(axis == ra and abs(pos - rp) < DEDUPE_MM for ra, rp in reserved):
                scored.append((score, axis, pos))
        if scored:
            best.append(max(scored, key=lambda s: (s[0], -s[2])))
    return _top_slices(best, max_cuts)


def _top_slices(best, max_cuts):
    best = sorted((b for b in best if b[0] >= MIN_SLICE_SCORE), key=lambda b: -b[0])
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
