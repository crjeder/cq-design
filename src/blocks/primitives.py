"""Primitive building blocks: basic shapes used as foundations for other blocks."""

import cadquery as cq


def fillet_box(
    w: float,
    d: float,
    h: float,
    r: float,
    centered: tuple[bool, bool, bool] = (True, True, False),
) -> cq.Workplane:
    """Rectangular box with filleted vertical edges.

    Args:
        w, d, h: outer dimensions in mm
        r: fillet radius on vertical edges
        centered: (x, y, z) centering flags; default places bottom at Z=0
    """
    return cq.Workplane("XY").box(w, d, h, centered=centered).edges("|Z").fillet(r)


def hollow_box(
    w: float, d: float, h: float, wall: float, floor_t: float, corner_r: float = 0.0
) -> cq.Workplane:
    """Open-top hollow box via boolean subtraction. Bottom at Z=0.

    Preferred over .shell() for stability with fillets and booleans.

    Args:
        w, d, h: outer dimensions in mm
        wall: wall thickness (min 1.2 mm for FDM)
        floor_t: floor thickness
        corner_r: outer corner fillet radius on vertical edges (0 = sharp)
    """
    outer = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if corner_r > 0:
        outer = outer.edges("|Z").fillet(corner_r)

    inner_r = max(0.1, corner_r - wall) if corner_r > 0 else 0.0
    inner = (
        cq.Workplane("XY")
        .workplane(offset=floor_t)
        .box(w - 2 * wall, d - 2 * wall, h, centered=(True, True, False))
    )
    if inner_r > 0:
        inner = inner.edges("|Z").fillet(inner_r)

    return outer.cut(inner)
