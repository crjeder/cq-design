"""Assembly-pose placement: map a union's local geometry into the shared frame.

A `placement` dict (from `BUILD_PLAN.json`) has an optional ordered `rotate` list of
`{axis, angle_deg}` steps and an optional `translate_mm` `[x, y, z]`. Rotations apply
in listed order about axes through the origin, then the translation. An absent or
empty placement is the identity.

Two appliers share this one convention:
  - `to_matrix(placement)` -> 4x4 numpy transform for trimesh / 3MF meshes
  - `apply_cq(workplane, placement)` -> CadQuery Workplane positioned in the frame

`apply_matrix(workplane, matrix)` is a third applier for a general 4x4 transform that
did not come from a `placement` dict -- namely a derived mate-chain pose
(`mate_chain.compute_mate_poses`), which does not generally decompose back into
`placement`'s ordered-rotation-then-translation shape.
"""

import math
from typing import Any

_AXIS_VEC = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}

Vec3 = tuple[float, float, float]


def _rotate_about_axis(v: Vec3, axis: str, angle_deg: float) -> Vec3:
    """Rotate a 3-vector about a principal axis by angle_deg (right-hand rule)."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = v
    if axis == "X":
        return (x, y * c - z * s, y * s + z * c)
    if axis == "Y":
        return (x * c + z * s, y, -x * s + z * c)
    if axis == "Z":
        return (x * c - y * s, x * s + y * c, z)
    raise KeyError(f"unknown rotation axis {axis!r}")


def transform_direction(vec: Any, placement: dict[str, Any] | None) -> Vec3:
    """Rotate a direction vector through a placement's ordered rotations (no translation).

    Pure-Python twin of `to_matrix` for the CadQuery/trimesh-free validation path: it
    matches `to_matrix`'s convention (rotations applied in listed order) without importing
    numpy or trimesh.
    """
    v: Vec3 = (float(vec[0]), float(vec[1]), float(vec[2]))
    for step in (placement or {}).get("rotate", []):
        v = _rotate_about_axis(v, step["axis"], step["angle_deg"])
    return v


def transform_point(pt: Any, placement: dict[str, Any] | None) -> Vec3:
    """Map a point through a placement: rotations (listed order) then translation."""
    v = transform_direction(pt, placement)
    translate = (placement or {}).get("translate_mm")
    if translate:
        v = (v[0] + translate[0], v[1] + translate[1], v[2] + translate[2])
    return v


def to_matrix(placement: dict[str, Any] | None) -> Any:
    """Return the 4x4 transform (numpy) for a placement: rotations then translation."""
    import numpy as np
    from trimesh.transformations import rotation_matrix, translation_matrix

    matrix = np.eye(4)
    if not placement:
        return matrix

    for step in placement.get("rotate", []):
        axis = _AXIS_VEC[step["axis"]]
        rot = rotation_matrix(np.radians(step["angle_deg"]), axis)
        matrix = rot @ matrix

    translate = placement.get("translate_mm")
    if translate:
        matrix = translation_matrix(translate) @ matrix

    return matrix


def _apply_trsf(workplane: Any, trsf: Any) -> Any:
    """Apply a `gp_Trsf` to each shape of a Workplane through the OCCT kernel.

    Uses `BRepBuilderAPI_Transform` on each shape's `.wrapped` (kernel copy flag) rather
    than `Workplane.rotate`/`translate`. This bypasses the patched `Shape._apply_transform`
    / `Shape.copy` that `cq_warehouse.extensions` installs, so no `copy.deepcopy` /
    `BinTools` serialization round-trip occurs.
    """
    from cadquery.occ_impl.shapes import Shape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

    transformed = [
        Shape.cast(BRepBuilderAPI_Transform(v.wrapped, trsf, True).Shape())
        for v in workplane.vals()
    ]
    return workplane.newObject(transformed)


def apply_cq(workplane: Any, placement: dict[str, Any] | None) -> Any:
    """Position a CadQuery Workplane by a placement: rotations then translation.

    The composed `gp_Trsf` is `T * R_n * ... * R_1`, matching `to_matrix`.
    """
    if not placement:
        return workplane

    from math import radians

    from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

    trsf = gp_Trsf()
    for step in placement.get("rotate", []):
        ax, ay, az = _AXIS_VEC[step["axis"]]
        rot = gp_Trsf()
        rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(ax, ay, az)), radians(step["angle_deg"]))
        trsf = rot.Multiplied(trsf)  # R_n * ... * R_1 (rotations in listed order)

    translate = placement.get("translate_mm")
    if translate:
        tr = gp_Trsf()
        tr.SetTranslation(gp_Vec(*translate))
        trsf = tr.Multiplied(trsf)  # translate after rotations

    return _apply_trsf(workplane, trsf)


def apply_matrix(workplane: Any, matrix: Any) -> Any:
    """Position a CadQuery Workplane by a general 4x4 transform (numpy).

    For a derived mate-chain pose (`mate_chain.compute_mate_poses`), which is a
    composition of rotate/translate steps and does not generally decompose back
    into a single ordered `placement`-shaped list. Builds the `gp_Trsf` from the
    matrix's top 3 rows (rotation + translation) via `SetValues`.
    """
    from OCP.gp import gp_Trsf

    m = matrix
    trsf = gp_Trsf()
    trsf.SetValues(
        m[0, 0], m[0, 1], m[0, 2], m[0, 3],
        m[1, 0], m[1, 1], m[1, 2], m[1, 3],
        m[2, 0], m[2, 1], m[2, 2], m[2, 3],
    )  # fmt: skip
    return _apply_trsf(workplane, trsf)
