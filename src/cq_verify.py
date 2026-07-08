"""Construction-time assertions for generated CadQuery part scripts.

Import these in a part script (the wrapper sets ``PYTHONPATH=<src>``) to catch
three silent failure modes at build time, where the offending feature can still
be named -- rather than downstream as a vague watertight/dimension symptom:

- ``verify_boolean`` -- a ``.cut()``/``.union()``/``.intersect()`` whose tool did
  not overlap, producing no change and no exception.
- ``verify_feature_bounds`` -- an added feature that pokes past the base body.
- ``check_workplane`` -- a workplane whose origin drifted (the ``.center()`` /
  ``.hole()`` origin-shift trap), silently placing a feature off-target.

All three raise a single marked ``RuntimeError`` on failure and return their
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
