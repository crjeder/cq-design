"""Connector building blocks: port cutouts, cable slots, ventilation grids."""

import math
import warnings

import cadquery as cq

# Subtractive solids overcut by this amount so the exit face is never coincident
# with the far face of the material (OCC boolean cuts are not fuzzy by default).
_EPS = 1e-4

# Below this diameter a plain horizontal cylinder self-bridges, so the
# self-supporting teardrop_post treatment adds little (advisory only).
_TEARDROP_POST_MIN_D = 3.0


def _drop_profile(r: float, angle: float, apex: str, flat: float = 0.0) -> cq.Workplane:
    """Drop-shaped cross-section in the XZ plane for self-supporting features.

    The half opposite ``apex`` is a circular arc of radius ``r``; the half toward
    ``apex`` is replaced by two straight faces running from the equator points
    ``(+/-r, 0)`` at ``angle`` from horizontal. With ``flat == 0`` they meet at a
    single apex point (the teardrop peak); with ``flat > 0`` they are truncated by
    a horizontal flat face of that width.

    Args:
        r: radius in mm
        angle: face angle from horizontal in degrees
        apex: ``"up"`` (peak at +Z, arc below) or ``"down"`` (peak/flat at -Z, arc above)
        flat: width of the truncating flat face in mm (0 = sharp apex)
    """
    sign = 1.0 if apex == "up" else -1.0
    arc_mid = (0, -r) if apex == "up" else (0, r)
    wp = cq.Workplane("XZ").moveTo(r, 0).threePointArc(arc_mid, (-r, 0))
    if flat <= 0:
        peak = r * math.tan(math.radians(angle))
        return wp.lineTo(0, sign * peak).close()
    f = flat / 2.0
    z_flat = sign * (r - f) * math.tan(math.radians(angle))
    return wp.lineTo(-f, z_flat).lineTo(f, z_flat).close()


def port_cutout(w: float, h: float, depth: float, chamfer: float = 0.5) -> cq.Workplane:
    """Rectangular opening for a connector port. Subtract from a wall.

    Chamfered edges ease print quality on vertical walls.

    Args:
        w: opening width in mm (e.g. USB-C: 9.0)
        h: opening height in mm (e.g. USB-C: 3.5)
        depth: wall thickness to cut through in mm
        chamfer: edge chamfer on Y-axis edges in mm (0 = sharp)
    """
    cutter = cq.Workplane("XY").box(w, depth + _EPS, h, centered=(True, False, False))
    if chamfer > 0:
        try:
            cutter = cutter.edges("|Y").chamfer(chamfer)
        except Exception:
            pass  # skip if chamfer fails on this geometry
    return cutter


def cable_slot(w: float, h: float, depth: float, chamfer: float = 0.5) -> cq.Workplane:
    """Elongated slot for cable routing through a wall or floor.

    Functionally identical to port_cutout but semantically for cables.

    Args:
        w: slot width in mm
        h: slot height in mm
        depth: material thickness to cut through in mm
        chamfer: edge chamfer in mm (0 = sharp)
    """
    cutter = cq.Workplane("XY").box(w, depth + _EPS, h, centered=(True, False, False))
    if chamfer > 0:
        try:
            cutter = cutter.edges("|Y").chamfer(chamfer)
        except Exception:
            pass
    return cutter


def vent_grid(
    cols: int, rows: int, slot_w: float, slot_l: float, spacing: float, depth: float
) -> cq.Workplane:
    """Grid of rectangular ventilation slots. Subtract from a face.

    Slots are aligned in a regular grid centered at origin.

    Args:
        cols: number of columns
        rows: number of rows
        slot_w: individual slot width in mm
        slot_l: individual slot length in mm
        spacing: gap between slots in mm
        depth: depth to cut (wall/floor thickness) in mm
    """
    total_w = cols * (slot_w + spacing) - spacing
    total_l = rows * (slot_l + spacing) - spacing

    positions = [
        (
            -total_w / 2 + c * (slot_w + spacing) + slot_w / 2,
            -total_l / 2 + r * (slot_l + spacing) + slot_l / 2,
        )
        for r in range(rows)
        for c in range(cols)
    ]

    return (
        cq.Workplane("XY")
        .pushPoints(positions)
        .rect(slot_w, slot_l)
        .extrude(depth + _EPS)
    )


def teardrop_bore(d: float, depth: float, angle: float = 45.0) -> cq.Workplane:
    """Self-supporting (drop-shaped) bore cutter for a horizontal hole.

    Use ONLY for horizontal bores (axis in the build plane). The lower half is a
    circular profile of diameter ``d``; the upper half is replaced by a ``^`` peak
    (two flat roof faces meeting at an apex) so every overhang stays within the
    printable limit and the hole roof self-supports without internal supports.
    The bore axis runs along +Y and the peak points +Z, so the part must print in
    its modeled orientation. Subtract from a wall with ``.cut()``.

    Args:
        d: bore diameter in mm (the circular lower portion)
        depth: wall thickness to cut through in mm
        angle: roof face angle from horizontal in degrees, default 45 (the
            overhang limit). Keep >= 45 for printability.
    """
    r = d / 2.0
    # Lower semicircle (r,0)->(0,-r)->(-r,0) with a ^ peak up to (0, r*tan(angle)).
    profile = _drop_profile(r, angle, apex="up")
    return profile.extrude(-(depth + _EPS))


def teardrop_post(
    d: float, length: float, angle: float = 45.0, flat: float = 1.2
) -> cq.Workplane:
    """Self-supporting horizontal solid peg (the additive dual of teardrop_bore).

    Use for a HORIZONTAL cylindrical protrusion (peg, pin, boss) printed in the
    build plane. The upper half is a circular arc of diameter ``d``; the lower half
    is replaced by two flat faces meeting a narrow flat bottom so the underside
    self-supports without supports. The axis runs along +Y and the flat bottom
    points -Z, so the part must print in its modeled orientation. Union onto a part
    with ``.union()``.

    Small features are advisory, never fatal: below ``d`` the requested ``flat`` is
    clamped to keep the inclined faces valid, and a ``warnings.warn`` is emitted when
    ``d`` is below the diameter where the treatment is useful. The block always
    returns a buildable solid. For a peg that must SEAT in a mating hole, prefer a
    45-degree-rotated cube (a diamond peg in a diamond hole), which self-supports on
    every face and locates positively.

    Args:
        d: cylinder diameter in mm (the circular upper portion)
        length: protrusion length along the axis in mm
        angle: underside face angle from horizontal in degrees, default 45 (the
            overhang limit). Keep >= 45 for printability.
        flat: width of the flat bottom in mm (default 1.2; 0 = sharp point)
    """
    r = d / 2.0
    eff_flat = flat
    if eff_flat >= d:
        eff_flat = d / 2.0
        warnings.warn(
            f"teardrop_post: flat={flat} >= d={d}; clamped to {eff_flat} mm to keep "
            "the self-supporting faces valid.",
            stacklevel=2,
        )
    if d < _TEARDROP_POST_MIN_D:
        warnings.warn(
            f"teardrop_post: d={d} mm is below {_TEARDROP_POST_MIN_D} mm; a plain "
            "horizontal cylinder self-bridges at this size, so the teardrop "
            "treatment adds little. Building anyway.",
            stacklevel=2,
        )
    profile = _drop_profile(r, angle, apex="down", flat=eff_flat)
    return profile.extrude(length)
