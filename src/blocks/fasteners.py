"""Fastener building blocks: screw bosses, standoffs, snap-fits, alignment features."""

import math

import cadquery as cq

# Subtractive solids overcut by this amount so the exit face is never coincident
# with the far face of the material (OCC boolean cuts are not fuzzy by default).
_EPS = 1e-4


def screw_boss(d_screw: float, d_outer: float, h: float) -> cq.Workplane:
    """Solid cylinder boss with central through-hole for a self-tapping screw.

    Union onto a floor, then the hole self-taps on first insert.

    Args:
        d_screw: screw shaft diameter in mm (hole size)
        d_outer: outer boss diameter in mm (recommend >= 2.5 * d_screw)
        h: boss height in mm
    """
    return cq.Workplane("XY").circle(d_outer / 2).extrude(h).faces(">Z").hole(d_screw)


def pcb_standoff(d_screw: float, d_outer: float, h: float) -> cq.Workplane:
    """Hollow cylindrical standoff for M2/M2.5/M3 PCB mounting screws.

    PCB sits on top face. Screw passes through PCB and into the standoff.

    Args:
        d_screw: screw clearance diameter in mm
        d_outer: outer diameter in mm (recommend >= 2 * d_screw)
        h: standoff height in mm
    """
    return cq.Workplane("XY").circle(d_outer / 2).extrude(h).faces(">Z").hole(d_screw)


def snap_hook_clip(w: float, length: float, h: float, hook_h: float) -> cq.Workplane:
    """Cantilever snap-fit hook clip.

    Mounts at Z=0, Y=0 (base face). Hook extends at the free end.
    The hook deflects in the +Y direction when mating. Use .cut() with
    snap_socket_receiver() on the mating part.

    Args:
        w: width (X) in mm
        length: cantilever length (Y) in mm
        h: beam thickness (Z) in mm
        hook_h: hook protrusion height in mm (the locking tooth)
    """
    beam = cq.Workplane("XY").box(w, length, h, centered=(True, False, False))
    # Hook tooth at the free end — sits proud of the beam top face
    hook = (
        cq.Workplane("XY")
        .workplane(offset=h)
        .transformed(offset=(0, length - hook_h, 0))
        .box(w, hook_h, hook_h, centered=(True, False, False))
    )
    return beam.union(hook)


def snap_socket_receiver(w: float, h: float, depth: float) -> cq.Workplane:
    """Rectangular slot to subtract from a wall to receive a snap_hook_clip.

    Subtract this from the mating part's wall face. Size to match the hook:
    w matches hook w, h slightly larger than hook_h, depth matches wall thickness.

    Args:
        w: slot width (X) in mm — match snap_hook_clip w
        h: slot height (Z) in mm — match snap_hook_clip hook_h + clearance
        depth: slot depth (Y) in mm — typically equal to wall thickness
    """
    return cq.Workplane("XY").box(w, depth + _EPS, h, centered=(True, False, False))


def alignment_pin(d: float, h: float) -> cq.Workplane:
    """Tapered cylindrical pin for press-fit part registration.

    Taper (1 deg inward) eases insertion. Mate with alignment_socket().

    Args:
        d: pin base diameter in mm
        h: pin height in mm
    """
    return cq.Workplane("XY").circle(d / 2).extrude(h, taper=1)


def alignment_socket(d: float, h: float, clearance: float = 0.2) -> cq.Workplane:
    """Receiving hole for alignment_pin. Subtract from the mating face.

    Args:
        d: pin base diameter in mm (must match alignment_pin d)
        h: socket depth in mm (match or exceed pin height)
        clearance: added to radius for fit (default 0.2 mm for FDM)
    """
    return cq.Workplane("XY").circle((d + clearance) / 2).extrude(h + _EPS)


def counterbore_hole(d_screw: float, d_head: float, h_head: float, depth: float) -> cq.Workplane:
    """Counterbore pocket + shaft clearance hole for socket head cap screws (ISO 4762).

    Subtract from your body. Head pocket at the top face; shaft clearance runs full depth.
    Standard sizes: M3 (d_screw=3.4, d_head=5.5, h_head=3.0),
    M4 (4.5, 7.0, 4.0), M5 (5.5, 8.5, 5.0).

    Args:
        d_screw: shaft clearance diameter in mm
        d_head: counterbore pocket diameter in mm
        h_head: counterbore pocket depth in mm
        depth: total hole depth in mm (must be >= h_head)
    """
    shaft = cq.Workplane("XY").circle(d_screw / 2).extrude(depth + _EPS)
    cbore = cq.Workplane("XY").workplane(offset=depth - h_head).circle(d_head / 2).extrude(h_head)
    return shaft.union(cbore)


def countersink_hole(
    d_screw: float, d_sink: float, depth: float, angle: float = 90
) -> cq.Workplane:
    """Countersink pocket + shaft clearance hole for flat-head screws (DIN 7991).

    Subtract from your body. Taper opens at the top face; shaft clearance runs full depth.
    Standard sizes: M3 (d_screw=3.2, d_sink=6.0), M4 (4.3, 8.0), M5 (5.3, 10.0).

    Args:
        d_screw: shaft clearance diameter in mm
        d_sink: countersink opening diameter at the top surface in mm
        depth: total hole depth in mm
        angle: included angle of the countersink in degrees (default 90, DIN 7991)
    """
    h_sink = (d_sink - d_screw) / 2 / math.tan(math.radians(angle / 2))
    shaft = cq.Workplane("XY").circle(d_screw / 2).extrude(depth + _EPS)
    cone = cq.Solid.makeCone(
        radius1=d_screw / 2,
        radius2=d_sink / 2,
        height=h_sink,
        pnt=cq.Vector(0, 0, depth - h_sink),
    )
    sink = cq.Workplane("XY").add(cone)
    return shaft.union(sink)


def hex_nut_trap(nut_flat: float, nut_h: float, depth: float, d_screw: float = 0) -> cq.Workplane:
    """Hexagonal pocket for a top-drop captured nut. Subtract from your body.

    Without d_screw: full-depth hex prism (use depth = nut_h + ~0.5 clearance).
    With d_screw: hex pocket (nut_h deep) at the top + screw clearance cylinder
    through full depth, so the bolt can pass below the nut.
    Standard sizes: M3 (nut_flat=5.5, nut_h=2.4), M4 (7.0, 3.2), M5 (8.0, 4.7).

    Args:
        nut_flat: across-flats distance in mm
        nut_h: nut thickness in mm; sets the hex pocket depth when d_screw > 0
        depth: total subtraction depth in mm
        d_screw: screw clearance diameter in mm (0 = no through-hole)
    """
    circumscribed_d = nut_flat / math.cos(math.pi / 6)
    if d_screw <= 0:
        return cq.Workplane("XY").polygon(6, circumscribed_d).extrude(depth + _EPS)
    hex_pocket = (
        cq.Workplane("XY")
        .workplane(offset=depth - nut_h)
        .polygon(6, circumscribed_d)
        .extrude(nut_h)
    )
    screw_cyl = cq.Workplane("XY").circle(d_screw / 2).extrude(depth + _EPS)
    return hex_pocket.union(screw_cyl)
