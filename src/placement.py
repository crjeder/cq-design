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
    """Position a CadQuery Workplane by a placement: rotations then translation."""
    if not placement:
        return workplane

    result = workplane
    for step in placement.get("rotate", []):
        axis = _AXIS_VEC[step["axis"]]
        result = result.rotate((0, 0, 0), axis, step["angle_deg"])

    translate = placement.get("translate_mm")
    if translate:
        result = result.translate(tuple(translate))

    return result
