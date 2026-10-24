"""Primitive building blocks: basic shapes used as foundations for other blocks.

The step primitives (`box`, `cylinder`, `cone`, `sphere`, `prism`, `revolve`) are the
only way a step script builds geometry no block covers. Each sits centered in XY with its
bottom at Z=0 (`sphere`: centered at the origin) and has a `*_probes` function. Entries
with cosmetic edge sets also have `*_edge_sets`: set name -> local-frame edges, which the
print-pose finishing pass chamfers or fillets from the plan instance's `edges`.
"""

import cadquery as cq

from probes import bbox, empty_at, solid_at


def box(w: float, d: float, h: float) -> cq.Workplane:
    """Rectangular solid w x d x h, centered in XY, bottom at Z=0."""
    return cq.Workplane("XY").box(w, d, h, centered=(True, True, False))


def box_probes(w: float, d: float, h: float) -> list:
    return [solid_at((0, 0, h / 2)), bbox((-w / 2, -d / 2, 0), (w / 2, d / 2, h))]


def box_edge_sets(w: float, d: float, h: float) -> dict:
    b = box(w, d, h)
    return {
        "top_outer": b.edges(">Z").vals(),
        "bottom_outer": b.edges("<Z").vals(),
        "vertical": b.edges("|Z").vals(),
    }


def cylinder(d: float, h: float) -> cq.Workplane:
    """Cylinder of diameter d along +Z, axis at the origin, bottom at Z=0."""
    return cq.Workplane("XY").circle(d / 2).extrude(h)


def cylinder_probes(d: float, h: float) -> list:
    return [solid_at((0, 0, h / 2)), bbox((-d / 2, -d / 2, 0), (d / 2, d / 2, h))]


def cylinder_edge_sets(d: float, h: float) -> dict:
    c = cylinder(d, h)
    return {"top": c.edges(">Z").vals(), "bottom": c.edges("<Z").vals()}


def cone(d1: float, d2: float, h: float) -> cq.Workplane:
    """Truncated cone along +Z: diameter d1 at Z=0, d2 at Z=h (either may be 0)."""
    return cq.Workplane("XY").add(
        cq.Solid.makeCone(d1 / 2, d2 / 2, h, cq.Vector(0, 0, 0), cq.Vector(0, 0, 1))
    )


def cone_probes(d1: float, d2: float, h: float) -> list:
    r = max(d1, d2) / 2
    return [solid_at((0, 0, h / 2)), bbox((-r, -r, 0), (r, r, h))]


def sphere(d: float) -> cq.Workplane:
    """Sphere of diameter d centered at the origin."""
    return cq.Workplane("XY").sphere(d / 2)


def sphere_probes(d: float) -> list:
    r = d / 2
    return [solid_at((0, 0, 0)), bbox((-r, -r, -r), (r, r, r))]


def prism(points: list, h: float) -> cq.Workplane:
    """Closed XY polyline `points` ([[x, y], ...], in place, not centered) extruded h along +Z."""
    return cq.Workplane("XY").polyline([tuple(p) for p in points]).close().extrude(h)


def prism_probes(points: list, h: float) -> list:
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return [bbox((min(xs), min(ys), 0), (max(xs), max(ys), h))]


def revolve(points: list, angle: float = 360.0) -> cq.Workplane:
    """Closed XZ polyline `points` ([[r, z], ...], r >= 0) revolved about the Z axis."""
    return (
        cq.Workplane("XZ")
        .polyline([tuple(p) for p in points])
        .close()
        .revolve(angle, (0, 0, 0), (0, 1, 0))
    )


def revolve_probes(points: list, angle: float = 360.0) -> list:
    r = max(p[0] for p in points)
    zs = [p[1] for p in points]
    if angle < 360:
        return []
    return [bbox((-r, -r, min(zs)), (r, r, max(zs)))]


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


def hollow_box_probes(
    w: float, d: float, h: float, wall: float, floor_t: float, corner_r: float = 0.0
) -> list:
    return [
        solid_at((0, 0, floor_t / 2), "floor"),
        empty_at((0, 0, (floor_t + h) / 2), "cavity"),
        solid_at((w / 2 - wall / 2, 0, (floor_t + h) / 2), "wall"),
        bbox((-w / 2, -d / 2, 0), (w / 2, d / 2, h)),
    ]


def hollow_box_edge_sets(w: float, d: float, h: float, wall: float, floor_t: float) -> dict:
    outer = box(w, d, h)
    return {
        "top_outer": outer.edges(">Z").vals(),
        "bottom_outer": outer.edges("<Z").vals(),
        "vertical_outer": outer.edges("|Z").vals(),
    }
