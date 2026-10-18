"""Construction-time assertions for generated CadQuery part scripts.

Import these in a part script (the wrapper sets ``PYTHONPATH=<src>``) to catch
silent failure modes at build time, where the offending feature can still be
named -- rather than downstream as a vague watertight/dimension symptom:

- ``verify_boolean`` -- a ``.cut()``/``.union()``/``.intersect()`` whose tool did
  not overlap, producing no change and no exception.
- ``verify_feature_bounds`` -- an added feature that pokes past the base body.
- ``check_workplane`` -- a workplane whose origin drifted (the ``.center()`` /
  ``.hole()`` origin-shift trap), silently placing a feature off-target.
- ``verify_stage`` -- a named construction stage whose bbox/volume doesn't match
  what the construction plan expected, catching a wrong-topology stage at the
  point it was introduced instead of several steps later.
- ``verify_backed`` -- a feature's mating face not fully backed by its intended
  neighboring feature (e.g. a standoff post only half-supported by the leg it
  stands on), catching a centerline-reused-as-boundary mistake at the point the
  feature was authored.
- ``verify_seated`` -- a flat support body seated at a round boss's *center*
  instead of its tangent (e.g. a hinge riser box whose top face lands on the
  knuckle disc's center), leaving the boss half-buried in the support.
- ``check_fillet`` / ``check_chamfer`` -- a fillet radius or chamfer length that cannot
  fit the adjacent edges, caught before OCC returns a vague construction error.
- ``check_ligament`` -- too little material between a centered hole and the wall edge.

All raise a single marked ``RuntimeError`` on failure and return their
post-operation argument on success, so they sit inline in the build chain. The
marker lets ``run_cadquery_model.py`` map the failure to a typed error; nothing
else parses it. Depends only on CadQuery + the standard library.
"""

# Machine-readable marker the wrapper keys on: "[cq-verify:<kind>:<label>] <detail>".
MARKER = "cq-verify"

# A boolean counts as a no-op only when all three are unchanged within these bounds.
_VOLUME_EPS_MM3 = 1e-3
_CENTROID_EPS_MM = 1e-2


def _fail(kind: str, label: str, detail: str) -> "RuntimeError":
    """Build the marked RuntimeError the wrapper classifies into a typed error."""
    return RuntimeError(f"[{MARKER}:{kind}:{label}] {detail}")


def _solid(obj):
    """Return the underlying CadQuery Shape from a Workplane (or the object itself)."""
    return obj.val() if hasattr(obj, "val") else obj


def _centroid(shape) -> tuple[float, float, float]:
    """Bounding-box center of a Shape, used as a cheap position signature."""
    bb = shape.BoundingBox()
    return (
        (bb.xmin + bb.xmax) / 2.0,
        (bb.ymin + bb.ymax) / 2.0,
        (bb.zmin + bb.zmax) / 2.0,
    )


def verify_boolean(before, after, operation: str = "cut", label: str = ""):
    """Raise if a boolean produced no change (volume, face count, centroid all equal)."""
    sb, sa = _solid(before), _solid(after)

    vol_before, vol_after = sb.Volume(), sa.Volume()
    faces_before, faces_after = len(sb.Faces()), len(sa.Faces())
    cb, ca = _centroid(sb), _centroid(sa)

    vol_changed = abs(vol_after - vol_before) > _VOLUME_EPS_MM3
    faces_changed = faces_after != faces_before
    centroid_shifted = sum(abs(a - b) for a, b in zip(ca, cb, strict=True)) > _CENTROID_EPS_MM

    if not vol_changed and not faces_changed and not centroid_shifted:
        raise _fail(
            "silent_boolean",
            label,
            f"{operation} produced no change (volume {vol_before:.3f} -> {vol_after:.3f} mm^3, "
            f"faces {faces_before} -> {faces_after}); the tool likely does not overlap the body",
        )
    return after


def verify_feature_bounds(before, after, label: str = "", tolerance: float = 0.1):
    """Raise if the post-feature geometry extends past the base body's bbox on any axis."""
    bb_before = _solid(before).BoundingBox()
    bb_after = _solid(after).BoundingBox()

    x_over = max(
        0.0, bb_after.xmax - bb_before.xmax - tolerance, bb_before.xmin - bb_after.xmin - tolerance
    )
    y_over = max(
        0.0, bb_after.ymax - bb_before.ymax - tolerance, bb_before.ymin - bb_after.ymin - tolerance
    )
    z_over = max(
        0.0, bb_after.zmax - bb_before.zmax - tolerance, bb_before.zmin - bb_after.zmin - tolerance
    )

    if x_over > 0 or y_over > 0 or z_over > 0:
        raise _fail(
            "feature_overflow",
            label,
            f"feature extends past the base bounding box: X {x_over:.2f} mm, "
            f"Y {y_over:.2f} mm, Z {z_over:.2f} mm",
        )
    return after


def check_workplane(wp, label: str = "", expected_origin=None, tolerance: float = 0.1):
    """Raise if the workplane origin drifted from expected_origin beyond tolerance."""
    if expected_origin is None:
        return wp

    origin = wp.plane.origin.toTuple()
    drift = sum((a - b) ** 2 for a, b in zip(origin, expected_origin, strict=True)) ** 0.5

    if drift > tolerance:
        raise _fail(
            "workplane_drift",
            label,
            f"origin drifted to ({origin[0]:.2f}, {origin[1]:.2f}, {origin[2]:.2f}) from expected "
            f"({expected_origin[0]:.2f}, {expected_origin[1]:.2f}, {expected_origin[2]:.2f}), "
            f"delta {drift:.3f} mm; re-anchor with .workplane(origin=...) or a fresh workplane",
        )
    return wp


def verify_stage(
    wp, label: str = "", bbox=None, vol_min: float | None = None, tolerance: float = 0.1
):
    """Raise if a named construction stage's bbox/volume doesn't match expectations.

    ``bbox`` is (xmin, xmax, ymin, ymax, zmin, zmax); at least one of ``bbox`` or
    ``vol_min`` must be supplied. Returns ``wp`` unchanged on success.
    """
    if bbox is None and vol_min is None:
        raise ValueError(f"verify_stage({label!r}): supply bbox and/or vol_min")

    shape = _solid(wp)

    if bbox is not None:
        bb = shape.BoundingBox()
        actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
        if any(abs(a - e) > tolerance for a, e in zip(actual, bbox, strict=True)):
            raise _fail(
                "stage_mismatch",
                label,
                f"bbox {tuple(round(v, 2) for v in actual)} does not match expected "
                f"{tuple(bbox)} within {tolerance} mm",
            )

    if vol_min is not None:
        volume = shape.Volume()
        if volume < vol_min:
            raise _fail(
                "stage_mismatch",
                label,
                f"volume {volume:.3f} mm^3 is below expected minimum {vol_min:.3f} mm^3",
            )

    return wp


# Signed axis token -> (bbox axis letter, sign of the feature's face on that axis).
_AXIS_TOKENS = {
    "+x": ("x", 1),
    "-x": ("x", -1),
    "+y": ("y", 1),
    "-y": ("y", -1),
    "+z": ("z", 1),
    "-z": ("z", -1),
}


def verify_backed(backer, feature, axis: str, label: str = "", tolerance: float = 0.1):
    """Raise if `feature`'s mating face (named by `axis`) is not fully backed by `backer`.

    `axis` is a signed token ("+x"/"-x"/"+y"/"-y"/"+z"/"-z") naming the direction from
    `feature`'s interior toward `backer` -- e.g. "-z" for a feature whose bottom face
    must rest on `backer`. Two bbox-only checks: `backer` must reach the contact plane,
    and `feature`'s extent on the two axes orthogonal to `axis` must be fully contained
    within `backer`'s extent there (the check that catches a feature only partially
    supported by its intended neighbor). Returns `feature` unchanged on success.
    """
    if axis not in _AXIS_TOKENS:
        raise ValueError(
            f"verify_backed({label!r}): axis must be one of {sorted(_AXIS_TOKENS)}, got {axis!r}"
        )

    bb_f = _solid(feature).BoundingBox()
    bb_b = _solid(backer).BoundingBox()
    axis_name, sign = _AXIS_TOKENS[axis]
    other_axes = [a for a in ("x", "y", "z") if a != axis_name]

    if sign < 0:
        contact = getattr(bb_f, f"{axis_name}min")
        reach = getattr(bb_b, f"{axis_name}max")
        reach_ok = reach >= contact - tolerance
    else:
        contact = getattr(bb_f, f"{axis_name}max")
        reach = getattr(bb_b, f"{axis_name}min")
        reach_ok = reach <= contact + tolerance

    if not reach_ok:
        raise _fail(
            "unbacked_mate",
            label,
            f"backer does not reach the contact plane on {axis} (feature face at "
            f"{contact:.2f} mm, backer extends to {reach:.2f} mm)",
        )

    for a in other_axes:
        f_min, f_max = getattr(bb_f, f"{a}min"), getattr(bb_f, f"{a}max")
        b_min, b_max = getattr(bb_b, f"{a}min"), getattr(bb_b, f"{a}max")
        if f_min < b_min - tolerance or f_max > b_max + tolerance:
            raise _fail(
                "unbacked_mate",
                label,
                f"feature not fully backed on {a}: feature range [{f_min:.2f}, "
                f"{f_max:.2f}] mm exceeds backer range [{b_min:.2f}, {b_max:.2f}] mm",
            )

    return feature


def verify_seated(support, boss, axis: str, label: str = "", overlap: float = 1.0):
    """Raise if a flat `support` body bites past the tangent plane of a round `boss`.

    `axis` is a signed token ("+x"/"-x"/"+y"/"-y"/"+z"/"-z") naming the direction from
    `boss` toward `support` -- e.g. "-z" for a riser standing below a hinge knuckle.
    Bbox-only: the bite depth is how far `support`'s bounding box extends past `boss`'s
    bounding-box tangent face on that axis. Fails when the bite exceeds `overlap`
    (default 1.0 mm, `pin_hinge`'s genuine-fusion margin), catching a flat body
    positioned at the round feature's *center* coordinate instead of its tangent so the
    boss ends up more than half-buried. Returns `boss` unchanged on success so it chains
    inline like the other verify_* helpers.
    """
    if axis not in _AXIS_TOKENS:
        raise ValueError(
            f"verify_seated({label!r}): axis must be one of {sorted(_AXIS_TOKENS)}, got {axis!r}"
        )

    bb_s = _solid(support).BoundingBox()
    bb_boss = _solid(boss).BoundingBox()
    axis_name, sign = _AXIS_TOKENS[axis]

    if sign < 0:
        tangent = getattr(bb_boss, f"{axis_name}min")
        bite = getattr(bb_s, f"{axis_name}max") - tangent
    else:
        tangent = getattr(bb_boss, f"{axis_name}max")
        bite = tangent - getattr(bb_s, f"{axis_name}min")

    if bite > overlap:
        raise _fail(
            "boss_swallowed",
            label,
            f"support bites {bite:.2f} mm past the boss tangent plane on {axis} "
            f"({tangent:.2f} mm), exceeding the {overlap:.2f} mm fusion margin; the flat "
            f"body is seated at the round feature's center, not its tangent",
        )
    return boss


def _edge_ends(edge) -> list:
    """Distinct end vertices of an edge (one for a closed edge such as a circle)."""
    uniq: list = []
    for v in edge.Vertices():
        if not any(v.isSame(u) for u in uniq):
            uniq.append(v)
    return uniq


def _size_limit(body, selector) -> tuple[float, float]:
    """Smallest (limit, edge_length) a fillet/chamfer size must stay below.

    For every edge sharing a vertex with a selected edge, the limit is its length,
    halved when both of its ends touch some other selected edge.
    """
    all_edges = _solid(body).Edges()
    sel = all_edges if selector is None else body.edges(selector).vals()
    touched = [(e, _edge_ends(e)) for e in sel]

    def touches(vertex, skip) -> bool:
        return any(
            not e.isSame(skip) and any(vertex.isSame(u) for u in ends) for e, ends in touched
        )

    best = (float("inf"), float("inf"))
    for a in all_edges:
        ends = _edge_ends(a)
        hit = [v for v in ends if touches(v, a)]
        if not hit:
            continue
        length = a.Length()
        limit = length / 2.0 if len(ends) == 2 and len(hit) == 2 else length
        best = min(best, (limit, length))
    return best


def _check_size(kind: str, noun: str, body, size: float, selector, label: str):
    limit, length = _size_limit(body, selector)
    if size >= limit:
        raise _fail(
            kind,
            label,
            f"{noun} {size:.2f} mm >= limit {limit:.2f} mm set by a {length:.2f} mm adjacent "
            f"edge (selector {selector!r}); keep it below the limit (e.g. {limit - 0.1:.2f} mm)",
        )
    return body


def check_fillet(body, radius: float, selector=None, label: str = ""):
    """Raise if a fillet of `radius` on the selected edges exceeds an adjacent edge's room."""
    return _check_size("fillet_radius", "radius", body, radius, selector, label)


def check_chamfer(body, length: float, selector=None, label: str = ""):
    """Raise if a symmetric chamfer of `length` on the selected edges exceeds the room."""
    return _check_size("chamfer_size", "length", body, length, selector, label)


def check_ligament(wall_mm: float, hole_d_mm: float, min_mm: float, label: str = "") -> float:
    """Raise if the material beside a centered hole is below `min_mm`; return the ligament."""
    ligament = (wall_mm - hole_d_mm) / 2.0
    if ligament < min_mm:
        raise _fail(
            "thin_ligament",
            label,
            f"ligament {ligament:.2f} mm < minimum {min_mm:.2f} mm "
            f"(wall {wall_mm:.2f} mm, hole {hole_d_mm:.2f} mm)",
        )
    return ligament
