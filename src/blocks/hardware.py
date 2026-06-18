"""Hardware blocks backed by cq_warehouse fastener geometry.

Requires cq_warehouse (already a project dependency). The module-level
extensions import activates Workplane.insertHole and related methods.
"""

import cadquery as cq
from cadquery import Solid

import cq_warehouse.extensions  # noqa: F401 -- side-effect: patches insertHole etc. onto Workplane


def heat_set_boss(
    size: str,
    d_outer: float,
    h: float,
    manufacturing_compensation: float = 0.1,
) -> cq.Workplane:
    """Printed cylinder boss with a heat-set threaded insert hole bored from the top.

    The insert pocket is sized using cq_warehouse dimensional data so the insert
    presses in cleanly. Union onto an enclosure floor; press the insert in from
    the top face after printing.

    Args:
        size: HeatSetNut size string 'Mx-pitch-length_mm', e.g. 'M3-0.5-6'.
              Valid: M2-0.4-3/4/6/8, M3-0.5-6/8/10, M4-0.7-6/8/10,
              M5-0.8-6/8/10, M6-1-10/12. Uses Hilitchi-style inserts.
        d_outer: outer boss diameter in mm (recommend >= 7 for M3, >= 9 for M4)
        h: boss height in mm (must be >= insert length encoded in size)
        manufacturing_compensation: radial compensation for FDM over-extrusion in mm
            (default 0.1; set 0 for non-FDM or when hole is undersized)
    """
    from cq_warehouse.fastener import HeatSetNut

    nut = HeatSetNut(size=size, fastener_type="Hilitchi", simple=True)
    return (
        cq.Workplane("XY")
        .circle(d_outer / 2)
        .extrude(h)
        .faces(">Z")
        .insertHole(nut, manufacturingCompensation=manufacturing_compensation)
    )


def socket_head_cap_screw(size: str, length: float) -> cq.Workplane:
    """ISO 4762 socket head cap screw solid for assembly visualization.

    Shaft points down (-Z), head sits on the XY plane at Z=0.
    Translate to the screw location after calling.

    Args:
        size: ISO metric thread spec, e.g. 'M3-0.5', 'M4-0.7', 'M5-0.8', 'M6-1'
        length: shaft length under the head in mm
    """
    from cq_warehouse.fastener import SocketHeadCapScrew

    screw = SocketHeadCapScrew(
        size=size, length=length, fastener_type="iso4762", simple=True
    )
    return cq.Workplane("XY").add(Solid(screw.wrapped))


def hex_head_screw(size: str, length: float) -> cq.Workplane:
    """ISO 4014 hex head bolt solid for assembly visualization.

    Shaft points down (-Z), head sits on the XY plane at Z=0.
    Translate to the screw location after calling.

    Args:
        size: ISO metric thread spec, e.g. 'M3-0.5', 'M4-0.7', 'M5-0.8', 'M6-1'
        length: shaft length under the head in mm
    """
    from cq_warehouse.fastener import HexHeadScrew

    screw = HexHeadScrew(size=size, length=length, fastener_type="iso4014", simple=True)
    return cq.Workplane("XY").add(Solid(screw.wrapped))


def hex_nut(size: str) -> cq.Workplane:
    """ISO 4032 hex nut solid for assembly visualization.

    Centered on the Z-axis, flat face on the XY plane.

    Args:
        size: ISO metric thread spec, e.g. 'M3-0.5', 'M4-0.7', 'M5-0.8', 'M6-1'
    """
    from cq_warehouse.fastener import HexNut

    nut = HexNut(size=size, fastener_type="iso4032", simple=True)
    return cq.Workplane("XY").add(Solid(nut.wrapped))
