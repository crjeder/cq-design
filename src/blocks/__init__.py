"""Parametric building blocks for CadQuery models.

Usage in model scripts:
    from blocks import fillet_box, hollow_box
    from blocks import pcb_standoff, screw_boss, snap_hook_clip
    from blocks import port_cutout, vent_grid, teardrop_bore
    from blocks import heat_set_boss, socket_head_cap_screw, hex_head_screw, hex_nut
    from blocks import counterbore_hole, countersink_hole, hex_nut_trap
"""

from blocks.primitives import fillet_box, hollow_box
from blocks.fasteners import (
    screw_boss,
    pcb_standoff,
    snap_hook_clip,
    snap_socket_receiver,
    alignment_pin,
    alignment_socket,
    counterbore_hole,
    countersink_hole,
    hex_nut_trap,
)
from blocks.connectors import (
    port_cutout,
    cable_slot,
    vent_grid,
    teardrop_bore,
    teardrop_post,
)
from blocks.hardware import (
    heat_set_boss,
    socket_head_cap_screw,
    hex_head_screw,
    hex_nut,
)
from blocks.joints import (
    dovetail_groove,
    dovetail_tongue,
    finger_joint,
    tenon,
    mortise,
    dowel_pin,
    dowel_bore,
    ball_stud,
    ball_socket,
    hinge_leaf,
    pin_hinge,
    living_hinge,
    shadow_gap,
)

__all__ = [
    "fillet_box",
    "hollow_box",
    "screw_boss",
    "pcb_standoff",
    "snap_hook_clip",
    "snap_socket_receiver",
    "alignment_pin",
    "alignment_socket",
    "counterbore_hole",
    "countersink_hole",
    "hex_nut_trap",
    "port_cutout",
    "cable_slot",
    "vent_grid",
    "teardrop_bore",
    "teardrop_post",
    "heat_set_boss",
    "socket_head_cap_screw",
    "hex_head_screw",
    "hex_nut",
    "dovetail_groove",
    "dovetail_tongue",
    "finger_joint",
    "tenon",
    "mortise",
    "dowel_pin",
    "dowel_bore",
    "ball_stud",
    "ball_socket",
    "hinge_leaf",
    "pin_hinge",
    "living_hinge",
    "shadow_gap",
]
