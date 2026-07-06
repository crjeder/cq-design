"""Part-to-part joint building blocks.

Joints are organized by a two-axis *functional* taxonomy used for selection:
- motion: rigid | hinge | ball (movement permitted after assembly)
- reversible: whether the joint separates non-destructively at its default fit

Reversibility is set by the `clearance` fit modifier, not the geometry: a positive
clearance yields a separable gap fit, a negative clearance yields an interference
(press) fit. The same geometry therefore moves between separable and permanent.

Internally the joints share three private construction cores (extrude-profile,
revolve, tiled-cylinder); these are implementation detail and not exposed.

Dovetail geometry derived from https://github.com/winksaville/cq-box-with-dovetail-lid
(MIT license, Wink Saville).
"""

import math

import cadquery as cq

# Subtractive solids overcut by this amount so the exit face is never coincident
# with the far face of the material (OCC boolean cuts are not fuzzy by default).
_EPS = 1e-4


# ---- shared cores -----------------------------------------------------------


def _extrude_profile(points: list[tuple[float, float]], length: float) -> cq.Workplane:
    """Extrude a closed 2D profile through the XZ plane along +Y by `length`.

    Points are (x, z) pairs in the XZ workplane (local x=world X, local y=world Z,
    normal=-Y). extrude(-length) sweeps from Y=0 to Y=+length.
    """
    wp = cq.Workplane("XZ").moveTo(*points[0])
    for x, z in points[1:]:
        wp = wp.lineTo(x, z)
    return wp.close().extrude(-length)


def _trapezoid_profile(
    half_top: float, half_base: float, depth: float
) -> list[tuple[float, float]]:
    """Dovetail trapezoid: opening (half_top) at Z=depth, base (half_base) at Z=0."""
    return [
        (-half_top, depth),
        (-half_base, 0),
        (half_base, 0),
        (half_top, depth),
    ]


def _cylinder_along_y(radius: float, length: float, y0: float, z_axis: float) -> cq.Workplane:
    """Cylinder of revolution whose axis runs +Y, from y0, at (x=0, z=z_axis)."""
    cyl = cq.Solid.makeCylinder(
        radius, length, pnt=cq.Vector(0, y0, z_axis), dir=cq.Vector(0, 1, 0)
    )
    return cq.Workplane("XY").add(cyl)


# ---- dovetail (extrude core) ------------------------------------------------


def dovetail_groove(
    width: float,
    wall: float,
    depth: float,
    length: float,
    angle: float = 55.0,
) -> cq.Workplane:
    """Sliding dovetail groove to subtract from a box top edge.

    Cross-section is a trapezoid wider at the base than the opening.
    Centered at X=0. Opening (narrow end) at Z=depth. Base (wide end) at Z=0.
    Solid extends from Y=0 to Y=length (slides in along +Y).

    Subtract from the body. Mate with dovetail_tongue() on the sliding lid.
    Typical placement: translate to (0, -box_d/2 + wall, box_h - depth).

    Args:
        width: outer box width in mm (groove spans width - 2*wall)
        wall: wall thickness in mm
        depth: groove depth in mm (equals lid thickness)
        length: groove length in mm (typically box_d - wall)
        angle: dovetail angle in degrees from vertical (default 55 = 35 deg overhang)
    """
    inner = width - 2 * wall
    flare = math.tan(math.radians(90 - angle)) * depth
    half_top = inner / 2
    half_base = half_top + flare
    return _extrude_profile(_trapezoid_profile(half_top, half_base, depth), length)


def dovetail_tongue(
    width: float,
    wall: float,
    depth: float,
    length: float,
    angle: float = 55.0,
    clearance: float = 0.1,
) -> cq.Workplane:
    """Sliding dovetail lid panel for a rectangular box.

    The tongue IS the lid — its height equals depth (lid thickness), so when
    placed in the groove the lid top is flush with the box top. No extra height
    is added. Callers that want surface features (text, vents) union them on top.

    Centered at X=0. Base at Z=0. Top at Z=depth. Slides along +Y into
    dovetail_groove(). Use clearance=0.1 for smooth sliding, 0.05 for snug.

    Args:
        width: outer box width in mm (must match dovetail_groove width)
        wall: wall thickness in mm (must match dovetail_groove wall)
        depth: tongue height in mm (equals lid thickness, must match groove depth)
        length: tongue length in mm (must match groove length)
        angle: dovetail angle in degrees from vertical (must match groove angle)
        clearance: clearance per side in mm subtracted from opening width (default 0.1)
    """
    inner = width - 2 * wall
    flare = math.tan(math.radians(90 - angle)) * depth
    half_top = (inner / 2) - clearance
    half_base = half_top + flare
    return _extrude_profile(_trapezoid_profile(half_top, half_base, depth), length)


# ---- dovetail corner / box joint (extrude core) -----------------------------


def _dovetail_comb(
    pin_count: int,
    pin_width: float,
    tail_width: float,
    board_thickness: float,
    tooth_length: float,
    flare_deg: float,
    grow: float = 0.0,
) -> cq.Workplane:
    """Tile `pin_count` dovetail-trapezoid teeth across X, centered about X=0.

    Each tooth's XZ cross-section is widest (`pin_width`) at the board face (Z=0)
    and narrows to `pin_width - 2*tan(flare_deg)*board_thickness` at the outer
    thickness face (Z=board_thickness), then extrudes `tooth_length` along +Y (the
    protrusion / insertion direction). `grow` offsets every trapezoid side outward
    by `grow` (the tail socket's per-side clearance; 0 for the pins); it leaves the
    flare slope and the tooth centres unchanged, so pins and tails stay aligned.
    """
    pitch = pin_width + tail_width
    total_width = pin_count * pin_width + (pin_count - 1) * tail_width
    half_base = pin_width / 2 + grow
    half_top = pin_width / 2 - math.tan(math.radians(flare_deg)) * board_thickness + grow
    profile = _trapezoid_profile(half_top, half_base, board_thickness)
    result: cq.Workplane | None = None
    for i in range(pin_count):
        x_center = -total_width / 2 + pin_width / 2 + i * pitch
        tooth = _extrude_profile(profile, tooth_length).translate((x_center, 0, 0))
        result = tooth if result is None else result.union(tooth)
    assert result is not None, "dovetail comb needs at least one pin (pin_count >= 1)"
    return result


def dovetail_corner_joint(
    pin_count: int,
    pin_width: float,
    tail_width: float,
    board_thickness: float,
    tooth_length: float,
    flare_deg: float = 15.0,
    corner_angle_deg: float = 90.0,
    clearance: float = 0.1,
) -> dict[str, cq.Workplane]:
    """Multi-pin dovetail CORNER (box) joint that joins two boards at a corner.

    This is the classic woodworking box-joint dovetail: alternating trapezoidal
    pins and matching tail sockets tiled across the shared corner edge, pressed
    straight together to lock the corner. This is NOT the sliding-rail
    ``dovetail_groove``/``dovetail_tongue`` pair (a lid sliding lengthwise into a
    slot); choose ``dovetail_corner_joint`` to join two separate boards end-to-end
    at a corner with mechanical pull-out resistance in the tooth plane.

    Returns the matched pair as a ``dict`` of two member unions
    ``{"pins": Workplane, "tails": Workplane}`` in one shared local frame:

    - ``"pins"`` is the positive comb. UNION it onto the end face of the pin board
      (the board whose face the teeth stick out of).
    - ``"tails"`` is the socket-shaped cutting tool. ``.cut()`` it from the end
      face of the tail board to open the matching sockets.

    The two boards are ordinarily SEPARATE parts: declare a ``joints`` entry with
    ``block: "dovetail_corner_joint"`` and
    ``members: [{member: "pins", part: <pin board>}, {member: "tails", part: <tail
    board>}]`` (each member's ``dock`` giving its pose in its own board's frame) so
    the mate chain derives the assembled corner. For a single monolithic printed
    part that carries both halves instead, declare them as the part's two ``unions``.

    Tolerance: ``clearance`` is a real per-side mating gap grown onto the ``"tails"``
    sockets only (``"pins"`` stays nominal). Positive (default 0.1) gives a
    separable gap fit; negative gives an interference (press) fit -- the same fit
    sign convention as ``dovetail_tongue``/``mortise``/``finger_joint``. The
    reference OpenSCAD had no clearance at all (a theoretical exact fit, i.e.
    ``clearance=0`` here).

    Angles -- two DISTINCT parameters, do not confuse them:

    - ``flare_deg`` is the per-tooth dovetail taper measured from the tooth's
      straight side (0 = a rectangular finger-joint tooth, larger = more undercut).
      This is NOT ``dovetail_groove``/``dovetail_tongue``'s ``angle`` (measured from
      vertical, opposite sense: larger there means shallower / more printable).
    - ``corner_angle_deg`` is the dihedral angle between the two boards, generalising
      the reference's hardcoded perpendicular corner (its ``rotate([-90, 0, 0])``).
      At the default 90 the ``"tails"`` member is the pin comb rotated -90 deg about
      the shared corner (X) edge, identical to the reference; other values rotate by
      ``-corner_angle_deg`` instead. It shapes ONLY the tooth/socket feature -- it
      does NOT miter the surrounding board bodies to meet flush at that angle; the
      caller's part scripts author each board face at the matching angle.

    PRINT FLAT with the tooth-tiling (X) edge in the build plane so the trapezoid
    undercuts self-support; a board printed teeth-up needs the flare shallow enough
    (small ``flare_deg``, or a chamfered lead-in) to stay under the overhang limit.

    Args:
        pin_count: number of pins (teeth) tiled across the corner edge (X)
        pin_width: pin width at the base (widest, at the board face) in mm (X)
        tail_width: gap between adjacent pins in mm -- the tail (socket) width (X)
        board_thickness: board thickness in mm; the trapezoid narrows over this (Z)
        tooth_length: protrusion / insertion length of each tooth in mm (Y),
            typically the mating board's thickness
        flare_deg: per-tooth dovetail taper from the straight side in degrees
            (default 15; 0 = rectangular tooth)
        corner_angle_deg: dihedral angle between the two boards in degrees
            (default 90 = perpendicular corner, matching the reference)
        clearance: per-side mating gap grown onto the tail sockets in mm
            (default 0.1; negative for an interference/press fit)
    """
    pins = _dovetail_comb(
        pin_count, pin_width, tail_width, board_thickness, tooth_length, flare_deg, grow=0.0
    )
    tails = _dovetail_comb(
        pin_count, pin_width, tail_width, board_thickness, tooth_length, flare_deg, grow=clearance
    )
    # Rotate the tail comb about the shared corner (X) edge so its insertion axis
    # meets the pin board at corner_angle_deg. -90 at the default reproduces the
    # reference's hardcoded rotate([-90, 0, 0]).
    tails = tails.rotate((0, 0, 0), (1, 0, 0), -corner_angle_deg)
    return {"pins": pins, "tails": tails}


# ---- finger / box joint (extrude core) --------------------------------------


def finger_joint(
    width: float,
    thickness: float,
    fingers: int,
    length: float,
    clearance: float = 0.1,
    start_high: bool = True,
) -> cq.Workplane:
    """Interlocking comb half of a finger (box) joint.

    Divides `width` into `fingers` equal slots along X and fills the alternating
    set selected by `start_high`. Call twice with opposite `start_high` to get the
    two interlocking halves. Fingers span Y=0..length and Z=0..thickness.

    Union onto the mating part edge. High shear + glue area; ideal for splitting a
    model so each half prints flat (load stays in-layer).

    Args:
        width: total joint span across the fingers in mm (X)
        thickness: finger height in mm (Z)
        fingers: number of equal slots across the width
        length: finger depth along the mate direction in mm (Y)
        clearance: per-side gap subtracted from each finger width in mm (default 0.1)
        start_high: True fills even slots, False fills odd slots (complementary halves)
    """
    pitch = width / fingers
    finger_w = pitch - 2 * clearance
    result = None
    for i in range(fingers):
        is_solid = (i % 2 == 0) if start_high else (i % 2 == 1)
        if not is_solid:
            continue
        x_center = -width / 2 + (i + 0.5) * pitch
        slot = (
            cq.Workplane("XY")
            .transformed(offset=(x_center, 0, 0))
            .box(finger_w, length, thickness, centered=(True, False, False))
        )
        result = slot if result is None else result.union(slot)
    assert result is not None, "finger joint needs at least one solid finger"
    return result


# ---- mortise & tenon (extrude core) -----------------------------------------


def tenon(w: float, h: float, length: float, clearance: float = 0.0) -> cq.Workplane:
    """Rectangular keyed peg. Union onto a part face; mate with mortise().

    Cross-section w (X) by h (Y), extruded `length` along +Z (mate axis). The
    rectangular section locks rotation, unlike a round alignment_pin. Centered in X
    and Y; base at Z=0.

    Args:
        w: peg width in mm (X)
        h: peg depth in mm (Y)
        length: peg length along the mate axis in mm (Z)
        clearance: per-side reduction of the cross-section in mm (default 0.0)
    """
    return cq.Workplane("XY").box(
        w - 2 * clearance, h - 2 * clearance, length, centered=(True, True, False)
    )


def mortise(w: float, h: float, depth: float, clearance: float = 0.2) -> cq.Workplane:
    """Rectangular pocket to subtract from a part for a tenon().

    Cross-section grown by clearance per side so the tenon seats with a fit.
    Use clearance > 0 for a slip fit, clearance < 0 for an interference (press) fit.

    Args:
        w: mating tenon width in mm (X)
        h: mating tenon depth in mm (Y)
        depth: pocket depth in mm (Z)
        clearance: per-side gap added to the cross-section in mm (default 0.2)
    """
    return cq.Workplane("XY").box(
        w + 2 * clearance, h + 2 * clearance, depth + _EPS, centered=(True, True, False)
    )


# ---- dowel pin & bore (revolve core) ----------------------------------------


def dowel_pin(d: float, length: float, chamfer: float = 0.4) -> cq.Workplane:
    """Cylindrical dowel with a lead-in chamfer at the inserting (top) end.

    Union onto a part, or print separately and press into two dowel_bore() holes
    to register split halves. Axis along Z, base at Z=0.

    Args:
        d: dowel diameter in mm
        length: dowel length in mm
        chamfer: lead-in chamfer at the top edge in mm (default 0.4, 0 disables)
    """
    pin = cq.Workplane("XY").circle(d / 2).extrude(length)
    if chamfer > 0:
        pin = pin.faces(">Z").chamfer(chamfer)
    return pin


def dowel_bore(d: float, depth: float, clearance: float = 0.1) -> cq.Workplane:
    """Bore to subtract for a dowel_pin. Fit is set by the sign of clearance.

    clearance > 0 yields a slip (separable) fit; clearance < 0 yields an
    interference (press, permanent) fit. For PLA a press fit is roughly -0.1 mm
    radial; remember FDM holes print undersized, so test on a coupon.

    Args:
        d: nominal dowel diameter in mm (match dowel_pin d)
        depth: bore depth in mm
        clearance: per-side gap added to the radius in mm (default 0.1, slip fit)
    """
    return cq.Workplane("XY").circle(d / 2 + clearance).extrude(depth + _EPS)


# ---- ball joint (revolve core) ----------------------------------------------


def ball_stud(d_ball: float, d_stem: float, stem_l: float, fillet: float = 2.0) -> cq.Workplane:
    """Ball on a stem for a ball-and-socket joint. Mate with ball_socket().

    The ball sits fully above the stem (ball bottom at Z=stem_l). A conical fillet
    blends the stem into the ball underside so it prints support-free with the stem
    pointing down. Axis along Z, stem base at Z=0.

    Args:
        d_ball: ball diameter in mm
        d_stem: stem diameter in mm
        stem_l: stem length in mm
        fillet: stem-to-ball conical blend height in mm (default 2.0, 0 disables)
    """
    r_ball = d_ball / 2.0
    stem = cq.Workplane("XY").circle(d_stem / 2).extrude(stem_l)
    ball = cq.Workplane("XY").sphere(r_ball).translate((0, 0, stem_l + r_ball))
    result = stem.union(ball)
    if 0 < fillet < d_ball:
        # cone top radius = sphere horizontal radius at height `fillet` above its base
        r_top = math.sqrt(max(d_ball * fillet - fillet * fillet, 1e-6))
        cone = cq.Solid.makeCone(d_stem / 2, r_top, fillet, pnt=cq.Vector(0, 0, stem_l))
        result = result.union(cq.Workplane("XY").add(cone))
    return result


def ball_socket(
    d_ball: float,
    retention_angle: float,
    slot_w: float,
    wall: float,
    clearance: float = 0.2,
) -> cq.Workplane:
    """Slotted snap-in socket that captures a ball past its equator.

    The internal cavity is a sphere of d_ball + 2*clearance. The cup wraps to
    `retention_angle` degrees past the equator, so the mouth opening is narrower
    than the ball and retains it. A slot of width slot_w through the retaining lip
    lets the cup flex during snap-in. Prints flat with the mouth facing up; base at
    Z=0.

    Args:
        d_ball: mating ball diameter in mm (must match ball_stud d_ball)
        retention_angle: degrees past the equator the cup grips (more = stronger hold)
        slot_w: flex slot width in mm
        wall: cup wall thickness in mm
        clearance: cavity radius added over the ball radius in mm (default 0.2)
    """
    r_cav = (d_ball + 2 * clearance) / 2.0
    theta = math.radians(retention_angle)
    center_z = wall + r_cav
    rim_z = center_z + r_cav * math.sin(theta)
    outer_r = r_cav + wall

    cup = cq.Workplane("XY").circle(outer_r).extrude(rim_z)
    cavity = cq.Workplane("XY").sphere(r_cav).translate((0, 0, center_z))
    socket = cup.cut(cavity)

    slot = (
        cq.Workplane("XY")
        .transformed(offset=(0, 0, center_z))
        .box(
            slot_w,
            2 * outer_r + _EPS,
            rim_z - center_z + _EPS,
            centered=(True, True, False),
        )
    )
    return socket.cut(slot)


# ---- hinge (tiled-cylinder core) --------------------------------------------


def pin_hinge(
    length: float,
    knuckles: int,
    leaf_w: float,
    leaf_t: float,
    d_filament: float = 1.9,
    clearance: float = 0.25,
) -> dict[str, cq.Workplane]:
    """Normal revolute knuckle hinge that pivots on a rigid pin (a 1.75 mm filament strand).

    This is an ordinary mechanical hinge: two RIGID leaves rotate freely about a
    separate pin (one revolute DOF about +Y, 0-180 deg), exactly like a door hinge.
    The pin happens to be a snipped strand of 1.75 mm filament, but the motion is the
    rotation of the pin, NOT material flex. This is NOT a living_hinge (a flexure that
    bends a thin web and has no pin); use pin_hinge whenever you need a durable,
    freely rotating, low-friction pivot. Treat it kinematically like any revolute hinge.

    Returns the two leaves as a `dict` of named member unions
    `{"leaf_a": Workplane, "leaf_b": Workplane}`: two coplanar flat leaves (opened flat
    at 180 deg) whose knuckles alternate along +Y and interleave on a shared axis, each
    bored by the same coaxial hole. They are separate bodies (joined in reality only by
    the pin), so a print-in-place hinge part declares them as two `unions` and the
    kinematic check can sweep one leaf against the other. After printing, push a snipped
    length of 1.75 mm filament through the coaxial bore as the pivot pin.

    The knuckle outer diameter is derived as d_filament + 2 mm (a 1 mm wall around the
    pin). Knuckles run at (X=0, Z=d_outer/2); leaf A extends -X, leaf B extends +X.

    PRINT FLAT with the knuckle axis (Y) in the build plane so the bore prints as a
    short horizontal bridge and the knuckle undersides self-support. The axial
    `clearance` between adjacent knuckles must exceed one layer height so the
    interleaved knuckles do not fuse.

    Args:
        length: total hinge length along the axis in mm (Y)
        knuckles: number of knuckle segments across the length
        leaf_w: flat leaf width in mm (X)
        leaf_t: flat leaf thickness in mm (Z)
        d_filament: pin bore diameter in mm (default 1.9, a slip fit over 1.75 mm
            filament since FDM holes print undersized)
        clearance: axial gap between adjacent knuckles in mm (default 0.25)
    """
    d_outer = d_filament + 2.0
    seg = length / knuckles
    z_axis = d_outer / 2
    bore = _cylinder_along_y(d_filament / 2, length + 2 * _EPS, -_EPS, z_axis)
    leaves: dict[str, cq.Workplane] = {}
    for side, key in (("A", "leaf_a"), ("B", "leaf_b")):
        x_dir = -1 if side == "A" else 1
        leaf_center_x = x_dir * (d_outer / 2 + leaf_w / 2)
        part = (
            cq.Workplane("XY")
            .transformed(offset=(leaf_center_x, 0, z_axis))
            .box(leaf_w, length, leaf_t, centered=(True, False, True))
        )
        # tab straddling the leaf-knuckle tangent so the two fuse into one solid
        # (a bare tangent line does not merge in OCC); placed only at this side's
        # knuckle Y-bands so it never reaches the opposing side's knuckles
        ov = min(leaf_w / 2, d_outer / 2, 1.0)
        for i in range(knuckles):
            is_this = (i % 2 == 0) if side == "A" else (i % 2 == 1)
            if not is_this:
                continue
            y0 = i * seg + clearance / 2
            klen = seg - clearance
            part = part.union(_cylinder_along_y(d_outer / 2, klen, y0, z_axis))
            tab = (
                cq.Workplane("XY")
                .transformed(offset=(x_dir * d_outer / 2, y0, z_axis))
                .box(2 * ov, klen, leaf_t, centered=(True, False, True))
            )
            part = part.union(tab)
        # Each leaf is bored by the same coaxial hole so the pin passes through both.
        leaves[key] = part.cut(bore)
    return leaves


# ---- living hinge (flat panel + thin web core) ------------------------------


def living_hinge(
    length: float,
    panel_w: float,
    panel_t: float,
    web_t: float = 0.6,
    web_w: float = 2.0,
) -> cq.Workplane:
    """Flexure hinge: two panels joined by a paper-thin web that BENDS (no pin).

    This is a one-piece FLEXURE: the thin web elastically bends; there is no axle and
    no moving parts. This is NOT a pin_hinge (which threads a separate filament
    pin through knuckles and rotates rigidly); use living_hinge for a thin one-piece
    fold line (lids, flat-pack walls), not a free-spinning pivot.

    Two rectangular panels (each panel_w wide in X, panel_t thick in Z) sit either
    side of a thin web of thickness web_t spanning web_w over the full `length` (Y, the
    fold axis). The web is flush with the +Z (top) face so the panels fold down, away
    from the web side. The whole part is one continuous body.

    PRINT FLAT with the fold axis (Y) in the build plane and the web continuous along
    Y, so the deposited filament paths run across the bend. MATERIAL MATTERS: PP, PETG,
    and TPU survive repeated folding; PLA is brittle and cracks after a few cycles.

    Args:
        length: hinge/panel length along the fold axis in mm (Y)
        panel_w: width of each panel in mm (X)
        panel_t: panel thickness in mm (Z)
        web_t: flexure web thickness in mm (default 0.6, a few FDM layers)
        web_w: flexure web width across the fold in mm (default 2.0)
    """

    def slab(x0: float, w: float, z0: float, t: float) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .transformed(offset=(x0 + w / 2, 0, z0 + t / 2))
            .box(w, length, t, centered=(True, False, True))
        )

    left = slab(-(web_w / 2 + panel_w), panel_w, 0, panel_t)
    right = slab(web_w / 2, panel_w, 0, panel_t)
    web = slab(-web_w / 2, web_w, panel_t - web_t, web_t)
    return left.union(web).union(right)


# ---- shadow gap (extruded lip core) -----------------------------------------


def shadow_gap(length: float, wall: float, overlap: float = 3.0) -> cq.Workplane:
    """Return-lip for an end-to-end seam that hides the real joint behind a reveal.

    When two parts meet end to end their butt seam always shows an irregular,
    tolerance-driven gap. This block is the tongue/return lip to union onto the inner
    face of the FRONT (visible) member at the seam plane (Y=0): a bar of `length` (X)
    by `overlap` (Y) by `wall` (Z, thickness) projecting in +Y behind the seam. The
    back member is then placed shortened by a deliberate reveal (~1 mm) and butted
    against the lip with a small clearance, so the only visible gap is the uniform
    recessed reveal while the real seam is concealed behind the front member's wall.

    Args:
        length: seam length along the front member edge in mm (X)
        wall: lip thickness in mm (Z), typically the member wall thickness
        overlap: how far the lip projects behind the seam to hide the back member in mm
            (default 3.0)
    """
    return cq.Workplane("XY").box(length, overlap, wall, centered=(True, False, True))
