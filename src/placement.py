"""Assembled-frame placement: map a union's local geometry into the shared frame.

A `placement` dict (from `BUILD_PLAN.json`) has an optional ordered `rotate` list of
`{axis, angle_deg}` steps and an optional `translate_mm` `[x, y, z]`. Rotations apply
in listed order about axes through the origin, then the translation. An absent or
empty placement is the identity.

Two appliers share this one convention:
  - `to_matrix(placement)` -> 4x4 numpy transform for trimesh / 3MF meshes
  - `apply_cq(workplane, placement)` -> CadQuery Workplane positioned in the frame
"""

from typing import Any

_AXIS_VEC = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


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


def apply_cq(workplane: Any, placement: dict[str, Any] | None) -> Any:
    """Position a CadQuery Workplane by a placement: rotations then translation.

    Applies the transform directly through the OCCT kernel
    (`BRepBuilderAPI_Transform` on each shape's `.wrapped`, with the kernel copy
    flag) rather than via `Workplane.rotate`/`translate`. This bypasses the
    patched `Shape._apply_transform`/`Shape.copy` that `cq_warehouse.extensions`
    installs, so no `copy.deepcopy` / `BinTools` serialization round-trip occurs.
    The composed `gp_Trsf` is `T * R_n * ... * R_1`, matching `to_matrix`.
    """
    if not placement:
        return workplane

    from math import radians

    from cadquery.occ_impl.shapes import Shape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
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

    transformed = [
        Shape.cast(BRepBuilderAPI_Transform(v.wrapped, trsf, True).Shape())
        for v in workplane.vals()
    ]
    return workplane.newObject(transformed)
