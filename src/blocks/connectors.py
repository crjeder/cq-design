"""Connector building blocks: port cutouts, cable slots, ventilation grids."""

import contextlib
import math
import warnings

import cadquery as cq

from probes import bbox, empty_at, solid_at

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


def _face_xz(
    solid: cq.Workplane, print_up: tuple[float, float, float] | None, base: tuple[float, float]
) -> cq.Workplane:
    """Rotate a Y-axis drop solid about Y so its ``base`` (x, z) direction faces print-up.

    ``base`` is where the feature points by default: the bore peak (+Z) or, for a post,
    the flat bottom, which must face away from print-up (so the caller passes -Z).
    No-op without ``print_up`` or when print-up runs along the axis (a vertical
    feature needs no teardrop).
    """
    if print_up is None:
        return solid
    ux, uz = print_up[0], print_up[2]
    if math.hypot(ux, uz) < 1e-6:
        return solid
    want = (ux, uz) if base[1] > 0 else (-ux, -uz)
    angle = math.degrees(math.atan2(want[0], want[1]) - math.atan2(base[0], base[1]))
    return solid.rotate((0, 0, 0), (0, 1, 0), angle)


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
        # skip if chamfer fails on this geometry
        with contextlib.suppress(Exception):
            cutter = cutter.edges("|Y").chamfer(chamfer)
    return cutter


def port_cutout_probes(w: float, h: float, depth: float, chamfer: float = 0.5) -> list:
    return [solid_at((0, depth / 2, h / 2)), bbox((-w / 2, 0, 0), (w / 2, depth, h))]


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
        with contextlib.suppress(Exception):
            cutter = cutter.edges("|Y").chamfer(chamfer)
    return cutter


cable_slot_probes = port_cutout_probes


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

    return cq.Workplane("XY").pushPoints(positions).rect(slot_w, slot_l).extrude(depth + _EPS)


def vent_grid_probes(
    cols: int, rows: int, slot_w: float, slot_l: float, spacing: float, depth: float
) -> list:
    total_w = cols * (slot_w + spacing) - spacing
    total_l = rows * (slot_l + spacing) - spacing
    z = depth / 2
    probes = [
        solid_at(
            (
                -total_w / 2 + c * (slot_w + spacing) + slot_w / 2,
                -total_l / 2 + r * (slot_l + spacing) + slot_l / 2,
                z,
            ),
            f"slot {r},{c}",
        )
        for r in range(rows)
        for c in range(cols)
    ]
    if cols > 1 and spacing > 0.2:
        probes.append(empty_at((-total_w / 2 + slot_w + spacing / 2, 0, z), "rib"))
    return [*probes, bbox((-total_w / 2, -total_l / 2, 0), (total_w / 2, total_l / 2, depth))]


def teardrop_bore(
    d: float,
    depth: float,
    angle: float = 45.0,
    peak: str = "up",
    print_up: tuple[float, float, float] | None = None,
) -> cq.Workplane:
    """Self-supporting (drop-shaped) bore cutter for a horizontal hole.

    Use ONLY for horizontal bores (axis in the build plane). The lower half is a
    circular profile of diameter ``d``; the upper half is replaced by a ``^`` peak
    (two flat roof faces meeting at an apex) so every overhang stays within the
    printable limit and the hole roof self-supports without internal supports.
    The bore axis runs along +Y and the peak points +Z, so the part must print in
    its modeled orientation unless ``peak="down"`` (see below). Subtract from a wall
    with ``.cut()``.

    The peak must face PRINT-up. When the part prints flipped so print-up is model
    -Z, pass ``peak="down"``; for a sideways print-up, rotate the cutter.

    Args:
        d: bore diameter in mm (the circular lower portion)
        depth: wall thickness to cut through in mm
        angle: roof face angle from horizontal in degrees, default 45 (the
            overhang limit). Keep >= 45 for printability.
        peak: ``"up"`` (peak at +Z, default) or ``"down"`` (peak at -Z)
        print_up: print-up direction in the build pose (``blocks.print_up()``);
            the peak is turned toward its XZ projection and overrides ``peak``.
    """
    if peak not in ("up", "down"):
        raise ValueError(f"teardrop_bore: peak must be 'up' or 'down', got {peak!r}")
    r = d / 2.0
    # Semicircle opposite the peak, with a peak at +/- r*tan(angle).
    bore = _drop_profile(r, angle, apex="down" if print_up is None and peak == "down" else "up")
    bore = bore.extrude(-(depth + _EPS))
    return _face_xz(bore, print_up, (0.0, 1.0))


def teardrop_bore_probes(
    d: float,
    depth: float,
    angle: float = 45.0,
    peak: str = "up",
    print_up: tuple[float, float, float] | None = None,
) -> list:
    return [solid_at((0, y, 0), "axis") for y in (min(0.2, depth / 4), depth / 2, depth - 0.2)]


def teardrop_post(
    d: float,
    length: float,
    angle: float = 45.0,
    flat: float = 1.2,
    print_up: tuple[float, float, float] | None = None,
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
        print_up: print-up direction in the build pose (``blocks.print_up()``);
            the flat bottom is turned to face away from its XZ projection.
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
    # The XZ workplane normal is -Y; extrude negative so the axis runs along +Y.
    return _face_xz(profile.extrude(-length), print_up, (0.0, -1.0))


def teardrop_post_probes(
    d: float,
    length: float,
    angle: float = 45.0,
    flat: float = 1.2,
    print_up: tuple[float, float, float] | None = None,
) -> list:
    return [solid_at((0, y, 0), "axis") for y in (min(0.2, length / 4), length / 2, length - 0.2)]
