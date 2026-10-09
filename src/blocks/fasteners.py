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
    Same geometry as `screw_boss`; kept as its own named block since the
    two represent distinct mounting intents in the block inventory.

    Args:
        d_screw: screw clearance diameter in mm
        d_outer: outer diameter in mm (recommend >= 2 * d_screw)
        h: standoff height in mm
    """
    return screw_boss(d_screw, d_outer, h)


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


def servo_spline(
    spline_external_diameter: float,
    shoe_height: float,
    tooth_count: int,
    tooth_depth: float,
    tooth_base_width: float,
    tooth_tip_width: float,
    clearance: float = 0.1,
) -> cq.Workplane:
    """Splined servo-shaft plug — subtract from a horn/arm to press-fit onto a servo.

    Reproduces the servo output spline (a toothed cylinder about +Z) as a solid
    cutter. `.cut()` it from the horn/arm body so the arm presses onto the servo's
    splined shaft. `clearance` radially enlarges the whole profile (core cylinder
    and every tooth) to set the fit: FDM prints holes undersized, so a small
    positive clearance (default 0.1 mm) lands a firm press fit at nominal; raise it
    for a looser slip, lower (toward 0 or negative) for a tighter interference.

    The teeth are radial trapezoids, wide (`tooth_base_width`) at the inner base and
    narrow (`tooth_tip_width`) at the outer tip, tiled `tooth_count` times around the
    axis. A central cylinder overlaps the tooth bases by a small fudge so the straight
    tooth flanks meet the round core without slivers. The plug axis is +Z, base at
    Z=0, top at Z=shoe_height.

    Common (SG90-class 25T) servo values:
    spline_external_diameter=5.92, shoe_height=4, tooth_count=25, tooth_depth=0.3,
    tooth_base_width=0.7, tooth_tip_width=0.1.

    Args:
        spline_external_diameter: outer tip-circle diameter of the spline in mm
        shoe_height: engagement depth (plug height along the axis) in mm
        tooth_count: number of spline teeth
        tooth_depth: radial tooth height (base to tip) in mm
        tooth_base_width: tangential tooth width at the base in mm
        tooth_tip_width: tangential tooth width at the tip in mm
        clearance: mm added to every radius for fit (default 0.1; lower = tighter press)
    """
    fudge = 0.055  # closes the gap where straight tooth flanks meet the round core
    r_base = spline_external_diameter / 2 - tooth_depth + clearance
    core_r = (spline_external_diameter - 2 * tooth_depth + 2 * clearance + fudge) / 2
    result = cq.Workplane("XY").circle(core_r).extrude(shoe_height)
    tooth_pts = [
        (tooth_tip_width / 2, r_base + tooth_depth),
        (tooth_base_width / 2, r_base),
        (-tooth_base_width / 2, r_base),
        (-tooth_tip_width / 2, r_base + tooth_depth),
    ]
    for i in range(tooth_count):
        tooth = (
            cq.Workplane("XY")
            .polyline(tooth_pts)
            .close()
            .extrude(shoe_height)
            .rotate((0, 0, 0), (0, 0, 1), i * 360.0 / tooth_count)
        )
        result = result.union(tooth)
    return result


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


def keeper_lock_eye(
    plate_d: float = 5.0,
    strap_w: float = 4.0,
    arch_t: float = 1.6,
    leg_inner_x: float = 5.0,
    leg_h: float = 12.5,
) -> cq.Workplane:
    """Eye half of a snap keeper lock: a flat U-arch that flexes outward (+Y).

    Mates with keeper_lock_hook; both are built in one shared assembled frame
    (X=0 centerline, Y=0 back faces, +Y outward, Z=0 at the arch leg bases),
    so the locked pair lines up without a transform. The arch bridge snaps into
    the hook's neck groove behind the head overhang. No backplate: the arch
    sits where the eye's plate front face would be and is meant to be fused
    into the host part.

    Args:
        plate_d: Y of the (omitted) plate front face in mm; arch front face is flush with it
        strap_w: arch strap width in the XZ plane in mm
        arch_t: arch strap thickness (Y) in mm; sets the flex stiffness
        leg_inner_x: arch inner radius = half the opening width in mm
        leg_h: straight leg length above Z=0 before the arc starts in mm
    """
    r_out = leg_inner_x + strap_w
    # XZ normal is -Y, so extrude(-t) grows into +Y
    return (
        cq.Workplane("XZ")
        .moveTo(-r_out, 0)
        .lineTo(-r_out, leg_h)
        .threePointArc((0, leg_h + r_out), (r_out, leg_h))
        .lineTo(r_out, 0)
        .lineTo(leg_inner_x, 0)
        .lineTo(leg_inner_x, leg_h)
        .threePointArc((0, leg_h + leg_inner_x), (-leg_inner_x, leg_h))
        .lineTo(-leg_inner_x, 0)
        .close()
        .extrude(-arch_t)
        .translate((0, plate_d - arch_t, 0))
    )


def keeper_lock_hook(
    eye_plate_d: float = 5.0,
    arch_t: float = 1.6,
    leg_h: float = 12.5,
    leg_inner_x: float = 5.0,
    clearance: float = 0.15,
    catch_overlap: float = 0.8,
    z_play: float = 0.7,
    side_gap: float = 0.5,
    neck_w: float = 7.0,
    head_l: float = 16.0,
    head_t: float = 1.8,
    ramp_len: float = 3.0,
    wall_min: float = 1.2,
) -> cq.Workplane:
    """Hook half of a snap keeper lock: pill-shaped neck + head stud (no backplate).

    Mates with keeper_lock_eye in the shared assembled frame (see keeper_lock_eye).
    Pass the eye's plate_d (as eye_plate_d), arch_t, leg_h and leg_inner_x: neck
    start, neck height, stud position and head width are derived from them, so
    the pair stays mated when either half is resized. The head has a lead-in ramp
    at its top end so the eye's arch bridge rides up and over it.

    Args:
        eye_plate_d: the eye's plate_d in mm (arch front face Y)
        arch_t: the eye's arch_t in mm
        leg_h: the eye's leg_h in mm
        leg_inner_x: the eye's leg_inner_x in mm
        clearance: gap between mating faces in mm; use the printer profile's
            fit_clearance_mm.snap_fit (0.15 default). Sets neck start Y and neck
            height
        catch_overlap: how far the head's top tip passes the arch inner apex (Z) in mm
        z_play: Z gap between the neck's top tip and the arch inner apex in mm
        side_gap: X gap per side between head and arch opening in mm
        neck_w: neck width (X) in mm
        head_l: head length (Z) in mm
        head_t: head thickness (Y) in mm; thicker = stiffer release
        ramp_len: lead-in ramp length along Z at the head's top end in mm
        wall_min: head thickness left at the top tip after the ramp in mm
    """
    plate_t = eye_plate_d - arch_t - clearance
    neck_t = eye_plate_d + clearance - plate_t
    head_w = 2 * leg_inner_x - 2 * side_gap
    apex_z = leg_h + leg_inner_x
    stud_zc = apex_z + catch_overlap - head_l / 2
    neck_l = 2 * (apex_z - z_play - stud_zc)
    head_y0 = plate_t + neck_t
    head_y1 = head_y0 + head_t
    head_top_z = stud_zc + head_l / 2
    # XZ normal is -Y, so extrude(-t) grows into +Y
    neck = (
        cq.Workplane("XZ", origin=(0, plate_t, 0))
        .moveTo(0, stud_zc)
        .slot2D(neck_l, neck_w, 90)
        .extrude(-neck_t)
    )
    head = (
        cq.Workplane("XZ", origin=(0, head_y0, 0))
        .moveTo(0, stud_zc)
        .slot2D(head_l, head_w, 90)
        .extrude(-head_t)
    )
    body = neck.union(head)
    ramp = (
        cq.Workplane("YZ")
        .polyline(
            [
                (head_y1, head_top_z - ramp_len),
                (head_y1 - (head_t - wall_min), head_top_z),
                (head_y1 + 1, head_top_z),
                (head_y1 + 1, head_top_z - ramp_len),
            ]
        )
        .close()
        .extrude(head_w, both=True)
    )
    return body.cut(ramp)
