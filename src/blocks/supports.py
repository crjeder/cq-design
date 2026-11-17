"""Designed-in breakaway support fins (see reference/support_fins.md).

Fin local frame: wall length along X (centred on 0), wall thickness along Y with the wall's
front face at y=0, height along +Z from z=0 (bed end) to z=height (top). The part face the fin
props up lies at y=``standoff``; horizontal tines cross that gap and overlap the part by
``tine_overlap``. Place with ``place_fin``.
"""

import math
from collections.abc import Sequence
from typing import cast

import cadquery as cq

from probes import bbox, solid_at

# Dimensions from Slant3D's published fin guidance (via support-fins FIN-SPEC.md); not yet
# print-tested here.
STANDOFF_MM = 0.2
TINE_OVERLAP_MM = 0.2
TINE_W_MIN_MM = 0.4
TINE_W_MAX_MM = 0.8
BASE_TINES = 5  # tine levels in the dense base cluster
UPPER_PITCH_LAYERS = 10  # layers between tine levels above the base cluster
PAD_T_MM = 1.0
_EPS = 1e-4


def _tine_levels(height: float, layer_h: float) -> list[float]:
    """Z of each tine level: BASE_TINES every second layer, then one per UPPER_PITCH_LAYERS."""
    levels = [2 * layer_h * (i + 1) for i in range(BASE_TINES)]
    z = levels[-1] + UPPER_PITCH_LAYERS * layer_h
    while z < height - layer_h:
        levels.append(z)
        z += UPPER_PITCH_LAYERS * layer_h
    return [lv for lv in levels if lv <= height - layer_h]


def breakaway_fin(
    height: float,
    length: float,
    layer_h: float = 0.2,
    tine_w: float = 0.4,
    wall_t: float = 0.8,
    standoff: float = STANDOFF_MM,
    tine_overlap: float = TINE_OVERLAP_MM,
    pad: bool = False,
    body: cq.Workplane | None = None,
) -> cq.Workplane:
    """One breakaway fin in its local frame: wall, rounded top, horizontal tines, optional pad.

    `body` (the part solid in the same frame, e.g. via `place_fin`'s inverse) enables the
    collision check: the wall may not intersect it (only the tines may, by `tine_overlap`).
    """
    if height <= 0 or length <= 0:
        raise ValueError(f"fin_invalid: height {height} and length {length} must be positive")
    if not TINE_W_MIN_MM <= tine_w <= TINE_W_MAX_MM:
        raise ValueError(f"fin_invalid: tine_w {tine_w} outside {TINE_W_MIN_MM}-{TINE_W_MAX_MM} mm")
    if height < 2 * layer_h * (BASE_TINES + 1):
        raise ValueError(f"fin_invalid: height {height} too small for {BASE_TINES} tine levels")

    wall = cq.Workplane("XY").box(length, wall_t, height, centered=(True, False, False))
    wall = wall.translate((0, -wall_t, 0)).faces(">Z").edges().fillet(wall_t * 0.45)

    xs = [0.0] if length < 8 else [-length / 2 + 2, 0.0, length / 2 - 2]
    y0, y1 = -wall_t / 2, standoff + tine_overlap
    fin = wall
    for z in _tine_levels(height, layer_h):
        for x in xs:
            tine = (
                cq.Workplane("XY")
                .box(tine_w, y1 - y0, layer_h, centered=(True, False, False))
                .translate((x, y0, z))
            )
            fin = fin.union(tine)

    if pad:
        rx, ry = length / 2 + 2, wall_t + 3
        disc = cq.Workplane("XY").ellipse(rx, ry).extrude(PAD_T_MM).translate((0, -wall_t / 2, 0))
        fin = fin.union(disc)

    if body is not None:
        overlap = cast(cq.Shape, wall.intersect(body).val()).Volume()
        if overlap > 1e-3:
            raise ValueError(f"fin_collision: wall intersects the part body by {overlap:.3f} mm3")
    return fin


def place_fin(
    fin: cq.Workplane,
    anchor: tuple[float, float, float],
    outward: tuple[float, float, float],
    up: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> cq.Workplane:
    """Move a local-frame fin so its (0, standoff, height) point sits on `anchor`.

    `outward` is the horizontal direction from the part toward the fin (the local -Y axis);
    `up` is the print-up direction in the frame the part is authored in (blocks.print_up()).
    The fin's top height is read from its bounding box, so the same fin works unmodified.
    """
    uz = _unit(up)
    ny = _unit(outward)
    # project outward onto the plane normal to up; local +Y points toward the part
    d = sum(a * b for a, b in zip(ny, uz, strict=True))
    ny = _unit(tuple(a - d * b for a, b in zip(ny, uz, strict=True)))
    uy = (-ny[0], -ny[1], -ny[2])
    ux = (
        uy[1] * uz[2] - uy[2] * uz[1],
        uy[2] * uz[0] - uy[0] * uz[2],
        uy[0] * uz[1] - uy[1] * uz[0],
    )
    shape = cast(cq.Shape, fin.val())
    top = shape.BoundingBox().zmax
    origin = cq.Vector(*anchor) - cq.Vector(*uy) * STANDOFF_MM - cq.Vector(*uz) * top
    plane = cq.Plane(origin=origin, xDir=cq.Vector(*ux), normal=cq.Vector(*uz))
    return cq.Workplane("XY").add(shape.transformShape(plane.rG))


def _unit(v: Sequence[float]) -> tuple[float, float, float]:
    n = math.sqrt(sum(c * c for c in v))
    if n < 1e-9:
        raise ValueError(f"fin_invalid: zero-length direction {v}")
    return (v[0] / n, v[1] / n, v[2] / n)


def breakaway_fin_probes(
    height: float,
    length: float,
    layer_h: float = 0.2,
    tine_w: float = 0.4,
    wall_t: float = 0.8,
    standoff: float = STANDOFF_MM,
    tine_overlap: float = TINE_OVERLAP_MM,
    pad: bool = False,
    body: cq.Workplane | None = None,
) -> list:
    return [
        solid_at((0, -wall_t / 2, height / 2), "wall"),
        bbox(size=(length, wall_t + standoff + tine_overlap, height), tol=0.5),
    ]
