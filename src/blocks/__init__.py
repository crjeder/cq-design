"""Parametric building blocks for CadQuery models.

Usage in model scripts (step form; see blocks.part):
    from blocks import Part

Legacy direct calls:
    from blocks import fillet_box, hollow_box
    from blocks import pcb_standoff, screw_boss, snap_hook_clip
    from blocks import port_cutout, vent_grid, teardrop_bore
    from blocks import heat_set_boss, socket_head_cap_screw, hex_head_screw, hex_nut
    from blocks import counterbore_hole, countersink_hole, hex_nut_trap
    from blocks import keeper_lock_eye, keeper_lock_hook
    from blocks import gridfinity_bin, gridfinity_baseplate, gridfinity_feet
"""

from blocks.connectors import (
    cable_slot,
    port_cutout,
    teardrop_bore,
    teardrop_post,
    vent_grid,
)
from blocks.fasteners import (
    alignment_pin,
    alignment_socket,
    counterbore_hole,
    countersink_hole,
    hex_nut_trap,
    keeper_lock_eye,
    keeper_lock_hook,
    pcb_standoff,
    screw_boss,
    servo_spline,
    snap_hook_clip,
    snap_socket_receiver,
)
from blocks.gridfinity import (
    gridfinity_baseplate,
    gridfinity_bin,
    gridfinity_dimensions,
    gridfinity_feet,
    gridfinity_socket_cutter,
    gridfinity_units_for,
)
from blocks.hardware import (
    heat_set_boss,
    hex_head_screw,
    hex_nut,
    socket_head_cap_screw,
)
from blocks.joints import (
    ball_socket,
    ball_stud,
    dovetail_corner_joint,
    dovetail_groove,
    dovetail_tongue,
    dowel_bore,
    dowel_pin,
    finger_joint,
    living_hinge,
    mortise,
    pin_hinge,
    shadow_gap,
    tenon,
)
from blocks.part import Part
from blocks.primitives import (
    box,
    cone,
    cylinder,
    fillet_box,
    hollow_box,
    prism,
    revolve,
    sphere,
    torus,
)
from blocks.print_frame import print_up

__all__ = [
    "Part",
    "box",
    "cylinder",
    "cone",
    "sphere",
    "prism",
    "revolve",
    "torus",
    "fillet_box",
    "hollow_box",
    "screw_boss",
    "pcb_standoff",
    "servo_spline",
    "snap_hook_clip",
    "snap_socket_receiver",
    "alignment_pin",
    "alignment_socket",
    "counterbore_hole",
    "countersink_hole",
    "hex_nut_trap",
    "keeper_lock_eye",
    "keeper_lock_hook",
    "port_cutout",
    "cable_slot",
    "vent_grid",
    "teardrop_bore",
    "teardrop_post",
    "print_up",
    "heat_set_boss",
    "socket_head_cap_screw",
    "hex_head_screw",
    "hex_nut",
    "dovetail_groove",
    "dovetail_tongue",
    "dovetail_corner_joint",
    "finger_joint",
    "tenon",
    "mortise",
    "dowel_pin",
    "dowel_bore",
    "ball_stud",
    "ball_socket",
    "pin_hinge",
    "living_hinge",
    "shadow_gap",
    "gridfinity_feet",
    "gridfinity_bin",
    "gridfinity_baseplate",
    "gridfinity_socket_cutter",
    "gridfinity_dimensions",
    "gridfinity_units_for",
]
