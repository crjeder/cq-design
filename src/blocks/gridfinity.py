"""Gridfinity building blocks: spec-conformant feet, bins, baseplates, and socket cutters.

Gridfinity is Zack Freedman's modular storage standard: everything sits on a 42 mm x 42 mm
grid, heights come in 7 mm units, and every bin's underside carries the same stepped foot
profile that mates with a baseplate socket (or with the stacking lip of the bin below).

The numbers below are the published standard (see `reference/gridfinity.md` for the
drawings they come from) -- they are fixed by the ecosystem, not design choices, so they
are module constants rather than parameters. Anything a designer legitimately varies
(wall thickness, floor height, dividers, magnet holes) is a keyword argument.

Frame convention, shared by every block here and matching the rest of the library: the
footprint is centered on the origin in X/Y and the print-bed face is Z = 0.

Usage in model scripts:
    from blocks import gridfinity_bin, gridfinity_baseplate
    result = gridfinity_bin(2, 1, 3, magnet_holes=True)
"""

import contextlib
import math
from typing import cast

import cadquery as cq

from probes import bbox, empty_at, solid_at

# --- Published Gridfinity standard -------------------------------------------------

#: Grid pitch: one Gridfinity unit (U) in X and Y.
GRID_PITCH_MM = 42.0
#: Height unit: bin body height is a whole multiple of this.
HEIGHT_UNIT_MM = 7.0
#: Gap between neighboring bins: a bin's footprint is ``42 * u - 0.5``.
GRID_CLEARANCE_MM = 0.5
#: Corner radius at the top of the foot profile (and of the bin body above it).
BASE_TOP_RADIUS_MM = 3.75
#: Height of the stepped foot profile itself (0.8 chamfer + 1.8 straight + 2.15 chamfer).
BASE_PROFILE_HEIGHT_MM = 4.75
#: Solid height under a bin's floor: the foot profile plus the bridge that ties feet
#: together. The default cavity floor sits here.
BASE_HEIGHT_MM = 7.0
#: Height of the stacking lip that sits on top of the bin body.
STACKING_LIP_HEIGHT_MM = 4.4
#: How far the stacking lip reaches inward from the bin's outer face.
STACKING_LIP_DEPTH_MM = 2.6
#: Magnet pocket: 6 mm x 2 mm disc magnets, hole sized for a press fit plus layer slop.
MAGNET_HOLE_D_MM = 6.5
MAGNET_HOLE_DEPTH_MM = 2.4
#: M3 screw hole through the foot (pairs with the magnet pocket above it).
SCREW_HOLE_D_MM = 3.0
SCREW_HOLE_DEPTH_MM = 6.0
#: Center-to-center spacing of the four magnet/screw holes within one grid cell.
HOLE_SPACING_MM = 26.0
#: Nominal exterior wall thickness; also the FDM-safe default here (3 perimeters @ 0.4 mm).
WALL_MM = 1.2
#: Wall thickness of the dividers between compartments.
DIVIDER_WALL_MM = 1.2
#: Fillet radius where a bin's cavity floor meets its walls.
FLOOR_FILLET_MM = 1.1
#: Nominal clearance of a baseplate socket around a bin foot, per side.
SOCKET_CLEARANCE_MM = 0.1
#: Fillet on the stacking lip's top outer edge. The standard draws two lip profiles, sharp
#: and rounded; the sharp one comes to a knife edge that no nozzle can lay down, so the
#: rounded profile is the default here. It touches nothing that mates -- the foot of the
#: bin above seats on the faces below it.
LIP_FILLET_MM = 0.6

# Foot profile, bottom-up, as (rise_mm, outward_mm) steps from the bottom pad. The two
# 45-degree chamfers are self-supporting; the straight section is the part that actually
# grips a baseplate socket.
_BASE_STEPS = ((0.8, 0.8), (1.8, 0.0), (2.15, 2.15))
# Stacking-lip recess profile, bottom-up from the lip's inner tip. It mirrors the foot
# profile with a slightly smaller reach, which is where the stacking clearance comes from.
_LIP_STEPS = ((0.7, 0.7), (1.8, 0.0), (1.9, 1.9))
# Baseplate socket profile, bottom-up from the socket's bottom pad.
_SOCKET_STEPS = ((0.7, 0.7), (1.8, 0.0), (2.25, 2.25))
# Straight run under a stacking lip's inner tip before the 45-degree support flares back
# out to the wall, so a lip thicker than its wall is not printed in mid-air.
_LIP_SUPPORT_H_MM = 1.2
# Overcut so a cutter's exit face is never coincident with the material's far face.
_EPS = 1e-3
# Below this a fillet on a rounded-rect section is a no-op (and OCC rejects radius 0).
_MIN_RADIUS_MM = 0.01


def lip_height(lip_fillet: float = LIP_FILLET_MM) -> float:
    """Built height of the stacking lip above the bin body, for a given rim fillet.

    Rounding the rim blunts a 45-degree wedge, so the apex drops by exactly sqrt(2) times
    the fillet radius -- the reason a finished bin measures a little under the nominal
    ``7 * height_u + 4.4``. Nothing that mates moves.
    """
    return STACKING_LIP_HEIGHT_MM - math.sqrt(2) * max(lip_fillet, 0.0)


def _rounded_rect_wire(w: float, d: float, r: float, z: float) -> cq.Wire:
    """Closed rounded-rect wire of `w` x `d` with corner radius `r`, at height `z`.

    Built explicitly (four lines, four arcs) rather than by filleting a sketch: every
    section then has identical topology, which is what keeps the ruled loft below exact
    and its result clean-able.
    """
    r = max(r, _MIN_RADIUS_MM)
    hw, hd = w / 2, d / 2
    k = r * math.sqrt(0.5)  # arc midpoint offset from the corner-arc center
    wp = (
        cq.Workplane("XY", origin=(0, 0, z))
        .moveTo(-hw + r, -hd)
        .lineTo(hw - r, -hd)
        .threePointArc((hw - r + k, -hd + r - k), (hw, -hd + r))
        .lineTo(hw, hd - r)
        .threePointArc((hw - r + k, hd - r + k), (hw - r, hd))
        .lineTo(-hw + r, hd)
        .threePointArc((-hw + r - k, hd - r + k), (-hw, hd - r))
        .lineTo(-hw, -hd + r)
        .threePointArc((-hw + r - k, -hd + r - k), (-hw + r, -hd))
        .close()
        .wire()
    )
    return cast(cq.Wire, wp.val())


def _lofted(sections: list[tuple[float, float, float, float]]) -> cq.Workplane:
    """Solid ruled-lofted through `(z, w, d, r)` rounded-rect sections, bottom-up.

    A ruled loft between two rounded rects whose corner-arc centers coincide gives exactly
    the straight walls and 45-degree conical corners the Gridfinity profiles are drawn
    with, with none of the version-dependent behavior of a tapered extrude.
    """
    wires = [_rounded_rect_wire(w, d, r, z) for z, w, d, r in sections]
    return cq.Workplane("XY").newObject([cq.Solid.makeLoft(wires, True)])


def _stepped_sections(
    w_top: float,
    d_top: float,
    r_top: float,
    steps: tuple[tuple[float, float], ...],
    z_top: float,
) -> list[tuple[float, float, float, float]]:
    """Loft sections for a stepped profile, given its top section and `(rise, out)` steps.

    Steps are listed bottom-up (as the standard draws them), so they are walked in reverse
    from the known top section down to the bottom pad.
    """
    sections = [(z_top, w_top, d_top, r_top)]
    z, w, d, r = z_top, w_top, d_top, r_top
    for rise, out in reversed(steps):
        z -= rise
        w -= 2 * out
        d -= 2 * out
        r -= out
        sections.append((z, w, d, r))
    return list(reversed(sections))


def _cell_centers(cols: int, rows: int) -> list[tuple[float, float]]:
    """Grid-cell center points for a `cols` x `rows` object centered on the origin."""
    return [
        ((c - (cols - 1) / 2) * GRID_PITCH_MM, (r - (rows - 1) / 2) * GRID_PITCH_MM)
        for c in range(cols)
        for r in range(rows)
    ]


def _hole_centers(cols: int, rows: int) -> list[tuple[float, float]]:
    """The four magnet/screw hole centers in every grid cell."""
    offset = HOLE_SPACING_MM / 2
    return [
        (cx + i * offset, cy + j * offset)
        for cx, cy in _cell_centers(cols, rows)
        for i in (-1, 1)
        for j in (-1, 1)
    ]


def _check_grid(cols: int, rows: int) -> None:
    if cols < 1 or rows < 1:
        raise ValueError(f"cols and rows must be >= 1 (got {cols}x{rows})")


def _bottom_holes(
    cols: int, rows: int, magnet_holes: bool, screw_holes: bool
) -> cq.Workplane | None:
    """Cutter for the magnet pockets and/or M3 screw holes in a foot array's underside."""
    cutter = None
    for enabled, diameter, depth in (
        (magnet_holes, MAGNET_HOLE_D_MM, MAGNET_HOLE_DEPTH_MM),
        (screw_holes, SCREW_HOLE_D_MM, SCREW_HOLE_DEPTH_MM),
    ):
        if not enabled:
            continue
        holes = (
            cq.Workplane("XY")
            .workplane(offset=-_EPS)
            .pushPoints(_hole_centers(cols, rows))
            .circle(diameter / 2)
            .extrude(depth + _EPS)
        )
        cutter = holes if cutter is None else cutter.union(holes)
    return cutter


def gridfinity_dimensions(
    cols: int = 1,
    rows: int = 1,
    height_u: int = 3,
    stacking_lip: bool = True,
    lip_fillet: float = LIP_FILLET_MM,
) -> dict[str, float]:
    """Outer dimensions of a Gridfinity bin, without building any geometry.

    Use when a plan or a mating part needs the numbers (`BUILD_PLAN.json` dimensions, a
    drawer's inner size, a keep-out zone) rather than the solid.

    Args:
        cols, rows: footprint in grid units (U), 42 mm each
        height_u: body height in height units (HU), 7 mm each
        stacking_lip: whether the returned height includes the stacking lip
        lip_fillet: the rim fillet the bin is built with, which sets how far the lip's
            apex is blunted (pass the same value used for `gridfinity_bin`)

    Returns:
        ``{"width", "depth", "height", "body_height", "floor_z", "stack_pitch"}`` in mm.
        ``height`` is what the part measures on the bed; ``stack_pitch`` is how much a
        stack grows per bin (7 mm x height_u), which is less than ``height`` because the
        bin above drops into the stacking lip.
    """
    _check_grid(cols, rows)
    body_h = height_u * HEIGHT_UNIT_MM
    return {
        "width": cols * GRID_PITCH_MM - GRID_CLEARANCE_MM,
        "depth": rows * GRID_PITCH_MM - GRID_CLEARANCE_MM,
        "height": body_h + (lip_height(lip_fillet) if stacking_lip else 0.0),
        "body_height": body_h,
        "floor_z": BASE_HEIGHT_MM,
        "stack_pitch": body_h,
    }


def gridfinity_feet(
    cols: int = 1,
    rows: int = 1,
    magnet_holes: bool = False,
    screw_holes: bool = False,
) -> cq.Workplane:
    """Array of Gridfinity feet: the stepped underside that docks into a baseplate.

    One foot per grid cell, bottom pad on the bed at Z = 0, top face at Z = 4.75 where each
    foot is a full 41.5 mm square. Union this under any custom body to make that body
    Gridfinity-compatible -- the body must start at Z = 4.75 and span no more than
    ``42 * cols - 0.5`` by ``42 * rows - 0.5`` so it bridges the feet without overhanging
    the grid. For a normal storage bin use `gridfinity_bin`, which does this for you.

    Args:
        cols, rows: footprint in grid units (U), 42 mm each
        magnet_holes: cut four 6.5 x 2.4 mm magnet pockets per cell
        screw_holes: cut four M3 (3.0 mm) screw holes per cell, coaxial with the magnets
    """
    _check_grid(cols, rows)
    pad = GRID_PITCH_MM - GRID_CLEARANCE_MM
    foot = _lofted(
        _stepped_sections(pad, pad, BASE_TOP_RADIUS_MM, _BASE_STEPS, BASE_PROFILE_HEIGHT_MM)
    )
    solid = cast(cq.Shape, foot.val())
    feet = cq.Workplane("XY").newObject(
        [solid.moved(cq.Location(cq.Vector(x, y, 0))) for x, y in _cell_centers(cols, rows)]
    )
    feet = feet.combine()

    holes = _bottom_holes(cols, rows, magnet_holes, screw_holes)
    return feet.cut(holes) if holes is not None else feet


def gridfinity_feet_probes(
    cols: int = 1, rows: int = 1, magnet_holes: bool = False, screw_holes: bool = False
) -> list:
    half_x = (cols * GRID_PITCH_MM - GRID_CLEARANCE_MM) / 2
    half_y = (rows * GRID_PITCH_MM - GRID_CLEARANCE_MM) / 2
    z = BASE_PROFILE_HEIGHT_MM / 2
    return [
        *(solid_at((x, y, z), "foot") for x, y in _cell_centers(cols, rows)),
        bbox((-half_x, -half_y, 0), (half_x, half_y, BASE_PROFILE_HEIGHT_MM)),
    ]


def gridfinity_socket_cutter(
    cols: int = 1,
    rows: int = 1,
    plate_h: float = BASE_PROFILE_HEIGHT_MM,
    clearance: float = SOCKET_CLEARANCE_MM,
) -> cq.Workplane:
    """Array of baseplate sockets as a subtractive solid: the negative of a bin's feet.

    Each socket's mouth sits at Z = `plate_h` (the plate's top face) and it flares downward
    to its pad 4.75 mm below. Cut this from any plate, drawer insert, or tool wall to make
    it hold Gridfinity bins. For a plain baseplate use `gridfinity_baseplate`.

    Args:
        cols, rows: footprint in grid units (U), 42 mm each
        plate_h: Z height of the plate's top face, where the socket mouths open
        clearance: extra size around the nominal foot, per side, for an easy drop-in fit
    """
    _check_grid(cols, rows)
    mouth = GRID_PITCH_MM + 2 * clearance
    radius = BASE_TOP_RADIUS_MM + GRID_CLEARANCE_MM / 2 + clearance
    sections = _stepped_sections(mouth, mouth, radius, _SOCKET_STEPS, plate_h)
    # Drop the pad a hair below its nominal depth so a socket in a minimum-thickness
    # (4.75 mm) plate cuts cleanly through instead of ending coincident with the underside.
    sections.insert(0, (sections[0][0] - _EPS, *sections[0][1:]))
    socket = _lofted(sections)
    # Cap the mouth so the cut is never coincident with the plate's top face.
    socket = socket.union(
        cq.Workplane("XY")
        .workplane(offset=plate_h)
        .rect(mouth, mouth)
        .extrude(_EPS)
        .edges("|Z")
        .fillet(radius)
    )
    solid = cast(cq.Shape, socket.val())
    placed = [solid.moved(cq.Location(cq.Vector(x, y, 0))) for x, y in _cell_centers(cols, rows)]
    # Neighboring mouths overlap by twice the clearance, so they are fused rather than
    # left as separate solids in one compound (which OCC booleans handle poorly).
    return cq.Workplane("XY").newObject(placed).combine()


def gridfinity_socket_cutter_probes(
    cols: int = 1, rows: int = 1, plate_h: float = 4.75, clearance: float = 0.1
) -> list:
    return [solid_at((x, y, plate_h / 2), "socket") for x, y in _cell_centers(cols, rows)]


def gridfinity_baseplate(
    cols: int = 1,
    rows: int = 1,
    plate_h: float = BASE_PROFILE_HEIGHT_MM,
    clearance: float = SOCKET_CLEARANCE_MM,
    magnet_holes: bool = False,
    screw_holes: bool = False,
) -> cq.Workplane:
    """Gridfinity baseplate: a `cols` x `rows` plate of sockets that bins drop into.

    Bottom face on the bed at Z = 0, outer footprint a full ``42 * cols`` by ``42 * rows``
    so baseplates tile edge to edge.

    Args:
        cols, rows: footprint in grid units (U), 42 mm each
        plate_h: total plate thickness; the default 4.75 mm is the minimum "light" plate,
            raise it to leave stock under the sockets for magnets or mounting screws
        clearance: socket clearance around a bin foot, per side
        magnet_holes: cut four 6.5 x 2.4 mm magnet pockets per cell into the underside
        screw_holes: cut four M3 through-holes per cell (for bolting the plate down)
    """
    _check_grid(cols, rows)
    if plate_h < BASE_PROFILE_HEIGHT_MM:
        raise ValueError(
            f"plate_h {plate_h} mm is thinner than the {BASE_PROFILE_HEIGHT_MM} mm socket "
            "profile; a baseplate cannot be thinner than the foot it holds"
        )
    stock_h = plate_h - BASE_PROFILE_HEIGHT_MM
    if (magnet_holes or screw_holes) and stock_h < MAGNET_HOLE_DEPTH_MM:
        raise ValueError(
            f"plate_h {plate_h} mm leaves only {stock_h:.2f} mm under the sockets; magnet or "
            f"screw holes need plate_h >= {BASE_PROFILE_HEIGHT_MM + MAGNET_HOLE_DEPTH_MM}"
        )

    plate = (
        cq.Workplane("XY")
        .box(cols * GRID_PITCH_MM, rows * GRID_PITCH_MM, plate_h, centered=(True, True, False))
        .edges("|Z")
        .fillet(BASE_TOP_RADIUS_MM + GRID_CLEARANCE_MM / 2)
    )
    plate = plate.cut(gridfinity_socket_cutter(cols, rows, plate_h=plate_h, clearance=clearance))

    # Magnet pockets open downward from the underside; the plate's screw holes go all the
    # way through, since they bolt the plate down rather than retain a magnet.
    holes = _bottom_holes(cols, rows, magnet_holes, False)
    if screw_holes:
        through = (
            cq.Workplane("XY")
            .workplane(offset=-_EPS)
            .pushPoints(_hole_centers(cols, rows))
            .circle(SCREW_HOLE_D_MM / 2)
            .extrude(plate_h + 2 * _EPS)
        )
        holes = through if holes is None else holes.union(through)
    return plate.cut(holes) if holes is not None else plate


def gridfinity_baseplate_probes(
    cols: int = 1,
    rows: int = 1,
    plate_h: float = 4.75,
    clearance: float = 0.1,
    magnet_holes: bool = False,
    screw_holes: bool = False,
) -> list:
    half_x, half_y = cols * GRID_PITCH_MM / 2, rows * GRID_PITCH_MM / 2
    socket_z = plate_h - BASE_PROFILE_HEIGHT_MM / 2
    probes = []
    for x, y in _cell_centers(cols, rows):
        probes.append(empty_at((x, y, socket_z), "socket"))
        probes.append(solid_at((x + GRID_PITCH_MM / 2 - 2, y, 0.3), "frame"))
    return [*probes, bbox((-half_x, -half_y, 0), (half_x, half_y, plate_h))]


def _cavity_sections(
    outer_l: float,
    outer_w: float,
    wall: float,
    floor_z: float,
    body_top: float,
    stacking_lip: bool,
) -> list[tuple[float, float, float, float]]:
    """Loft sections for a bin's interior cut, floor upward through the stacking lip."""
    inner = (outer_l - 2 * wall, outer_w - 2 * wall, BASE_TOP_RADIUS_MM - wall)
    sections = [(floor_z, *inner)]

    if not stacking_lip:
        sections.append((body_top + _EPS, *inner))
        return sections

    tip = (
        outer_l - 2 * STACKING_LIP_DEPTH_MM,
        outer_w - 2 * STACKING_LIP_DEPTH_MM,
        BASE_TOP_RADIUS_MM - STACKING_LIP_DEPTH_MM,
    )
    overhang = STACKING_LIP_DEPTH_MM - wall
    if overhang > 0:
        # 45-degree support ramp: the cavity necks in from the wall to the lip's inner tip
        # so the lip is printed on solid material rather than in mid-air.
        sections.append((body_top - _LIP_SUPPORT_H_MM - overhang, *inner))
        sections.append((body_top - _LIP_SUPPORT_H_MM, *tip))
    else:
        sections.append((body_top - _LIP_SUPPORT_H_MM, *inner))
    sections.append((body_top, *tip))
    # The recess that receives the foot of the bin stacked on top.
    lip_top = body_top + STACKING_LIP_HEIGHT_MM
    sections.extend(
        _stepped_sections(outer_l, outer_w, BASE_TOP_RADIUS_MM, _LIP_STEPS, lip_top)[1:]
    )
    # Carry the final 45-degree flare past the top face so the cutter exits the blank
    # instead of ending coincident with its outer walls.
    sections.append((lip_top + 1.0, outer_l + 2.0, outer_w + 2.0, BASE_TOP_RADIUS_MM + 1.0))
    return sections


def _label_tab(inner_l: float, inner_w: float, body_top: float, depth: float) -> cq.Workplane:
    """Sloped label shelf hanging from the +Y wall, top surface flush with the wall top."""
    y_wall = inner_w / 2
    profile = [
        (y_wall, body_top),
        (y_wall - depth, body_top),
        (y_wall - depth, body_top - _LIP_SUPPORT_H_MM),
        # 45-degree underside so the shelf needs no support.
        (y_wall, body_top - _LIP_SUPPORT_H_MM - depth),
    ]
    return cq.Workplane("YZ").polyline(profile).close().extrude(inner_l / 2, both=True)


def _scoop(inner_l: float, inner_w: float, floor_z: float, radius: float) -> cq.Workplane:
    """Quarter-round fill along the -Y wall so contents can be swept out with a finger."""
    y_wall = -inner_w / 2
    block = (
        cq.Workplane("XY")
        .workplane(offset=floor_z)
        .box(inner_l, radius, radius, centered=(True, False, False))
        .translate((0, y_wall, 0))
    )
    cylinder = (
        cq.Workplane("YZ")
        .workplane(offset=-inner_l / 2 - _EPS)
        .center(y_wall + radius, floor_z + radius)
        .circle(radius)
        .extrude(inner_l + 2 * _EPS)
    )
    return block.cut(cylinder)


def _dividers(
    inner_l: float,
    inner_w: float,
    floor_z: float,
    body_top: float,
    divisions_x: int,
    divisions_y: int,
    wall: float,
) -> cq.Workplane | None:
    """Compartment walls splitting the cavity into `divisions_x` x `divisions_y` cells."""
    height = body_top - floor_z
    walls = None
    for count, span, along_x in ((divisions_x, inner_l, True), (divisions_y, inner_w, False)):
        for i in range(1, count):
            offset = -span / 2 + i * span / count
            size = (wall, inner_w, height) if along_x else (inner_l, wall, height)
            position = (offset, 0.0) if along_x else (0.0, offset)
            plate = (
                cq.Workplane("XY")
                .workplane(offset=floor_z)
                .box(*size, centered=(True, True, False))
                .translate((*position, 0))
            )
            walls = plate if walls is None else walls.union(plate)
    return walls


def gridfinity_bin(
    cols: int = 1,
    rows: int = 1,
    height_u: int = 3,
    wall: float = WALL_MM,
    floor_z: float = BASE_HEIGHT_MM,
    stacking_lip: bool = True,
    magnet_holes: bool = False,
    screw_holes: bool = False,
    divisions_x: int = 1,
    divisions_y: int = 1,
    label_tab: bool = False,
    label_depth: float = 12.0,
    scoop: bool = False,
    scoop_radius: float = 8.0,
    floor_fillet: float = FLOOR_FILLET_MM,
    lip_fillet: float = LIP_FILLET_MM,
    solid: bool = False,
) -> cq.Workplane:
    """Gridfinity storage bin: feet, walls, cavity, and stacking lip, ready to print.

    Feet on the bed at Z = 0, body top at ``7 * height_u``, and (with the lip) 4.4 mm of
    stacking lip above that. A stack still grows by exactly ``7 * height_u`` per bin
    because the bin above drops into the lip.

    Pass ``solid=True`` for a blank with no cavity -- the starting point for a custom
    tool/part holder, where the pockets are cut to the shape of what they hold.

    Args:
        cols, rows: footprint in grid units (U), 42 mm each
        height_u: body height in height units (HU), 7 mm each; >= 2 for a usable cavity
        wall: side wall thickness in mm
        floor_z: Z height of the cavity floor; the default 7.0 is the standard solid base
        stacking_lip: build the lip that lets another bin stack on top
        magnet_holes: cut four 6.5 x 2.4 mm magnet pockets per cell into the feet
        screw_holes: cut four M3 screw holes per cell, coaxial with the magnets
        divisions_x, divisions_y: number of compartments along X and Y (1 = undivided)
        label_tab: add a sloped label shelf along the +Y wall
        label_depth: how far the label shelf reaches into the bin
        scoop: add a swept quarter-round at the -Y wall for scooping contents out
        scoop_radius: radius of that quarter-round
        floor_fillet: fillet radius where the cavity floor meets the walls (0 = sharp)
        lip_fillet: fillet on the stacking lip's top outer edge (0 = the sharp profile,
            which comes to a knife edge thinner than one extrusion)
        solid: skip the cavity (and dividers/label/scoop) and return a solid blank
    """
    _check_grid(cols, rows)
    if height_u < 1:
        raise ValueError(f"height_u must be >= 1 (got {height_u})")
    if wall <= 0:
        raise ValueError(f"wall must be > 0 (got {wall})")

    outer_l = cols * GRID_PITCH_MM - GRID_CLEARANCE_MM
    outer_w = rows * GRID_PITCH_MM - GRID_CLEARANCE_MM
    body_top = height_u * HEIGHT_UNIT_MM
    blank_top = body_top + (STACKING_LIP_HEIGHT_MM if stacking_lip else 0.0)

    body = (
        cq.Workplane("XY")
        .workplane(offset=BASE_PROFILE_HEIGHT_MM)
        .box(outer_l, outer_w, blank_top - BASE_PROFILE_HEIGHT_MM, centered=(True, True, False))
        .edges("|Z")
        .fillet(BASE_TOP_RADIUS_MM)
    )
    result = gridfinity_feet(cols, rows).union(body)

    if not solid:
        if floor_z >= body_top:
            raise ValueError(
                f"floor_z {floor_z} mm is at or above the body top ({body_top} mm): "
                f"a bin with height_u={height_u} has no cavity. Increase height_u."
            )
        if 2 * wall >= min(outer_l, outer_w):
            raise ValueError(f"wall {wall} mm leaves no cavity in a {cols}x{rows} bin")
        cavity = _lofted(_cavity_sections(outer_l, outer_w, wall, floor_z, body_top, stacking_lip))
        if floor_fillet > _MIN_RADIUS_MM:
            # Filleting the cutter's bottom loop leaves a concave fillet in the cavity.
            cavity = cavity.edges("<Z").fillet(min(floor_fillet, BASE_TOP_RADIUS_MM - wall))
        result = result.cut(cavity)

        inner_l = outer_l - 2 * wall
        inner_w = outer_w - 2 * wall
        if scoop:
            if scoop_radius > min(inner_w / 2, body_top - floor_z):
                raise ValueError(
                    f"scoop_radius {scoop_radius} mm does not fit the cavity "
                    f"({inner_w:.1f} mm deep, {body_top - floor_z:.1f} mm tall)"
                )
            result = result.union(_scoop(inner_l, inner_w, floor_z, scoop_radius))
        if label_tab:
            if label_depth >= inner_w:
                raise ValueError(
                    f"label_depth {label_depth} mm exceeds the {inner_w:.1f} mm cavity depth"
                )
            result = result.union(_label_tab(inner_l, inner_w, body_top, label_depth))
        if divisions_x > 1 or divisions_y > 1:
            walls = _dividers(
                inner_l, inner_w, floor_z, body_top, divisions_x, divisions_y, DIVIDER_WALL_MM
            )
            if walls is not None:
                result = result.union(walls)

        if stacking_lip and lip_fillet > _MIN_RADIUS_MM:
            # The rim is the only edge at the top; if the selection or the fillet fails on
            # unusual parameters, the sharp spec profile stands and the wrapper's
            # thin-wall check reports it rather than the bin failing to build.
            with contextlib.suppress(Exception):
                result = result.edges(">Z").fillet(lip_fillet)

    holes = _bottom_holes(cols, rows, magnet_holes, screw_holes)
    return result.cut(holes) if holes is not None else result


def gridfinity_bin_probes(
    cols: int = 1,
    rows: int = 1,
    height_u: int = 3,
    wall: float = WALL_MM,
    floor_z: float = BASE_HEIGHT_MM,
    stacking_lip: bool = True,
    magnet_holes: bool = False,
    screw_holes: bool = False,
    divisions_x: int = 1,
    divisions_y: int = 1,
    label_tab: bool = False,
    label_depth: float = 12.0,
    scoop: bool = False,
    scoop_radius: float = 8.0,
    floor_fillet: float = FLOOR_FILLET_MM,
    lip_fillet: float = LIP_FILLET_MM,
    solid: bool = False,
) -> list:
    # A solid blank skips the rim fillet, so its lip stands at full height.
    dims = gridfinity_dimensions(cols, rows, height_u, stacking_lip, 0.0 if solid else lip_fillet)
    half_x, half_y = dims["width"] / 2, dims["depth"] / 2
    body_top = height_u * HEIGHT_UNIT_MM
    probes = [
        solid_at((x, y, BASE_PROFILE_HEIGHT_MM / 2), "foot") for x, y in _cell_centers(cols, rows)
    ]
    probes.append(solid_at((half_x - wall / 2, 0, (floor_z + body_top) / 2), "wall"))
    if solid:
        probes.append(solid_at((0, 0, (floor_z + body_top) / 2), "solid body"))
    else:
        probes.append(solid_at((0, 0, (BASE_PROFILE_HEIGHT_MM + floor_z) / 2), "floor"))
        if not (scoop or label_tab):
            # 2 mm off the -X wall: clear of any divider, which sits >= one division in.
            cavity = (-half_x + wall + 2, 0, (floor_z + body_top) / 2)
            probes.append(empty_at(cavity, "cavity"))
    return [*probes, bbox((-half_x, -half_y, 0), (half_x, half_y, dims["height"]))]


def gridfinity_units_for(
    length_mm: float, width_mm: float, height_mm: float, clearance: float = 1.0
) -> dict[str, int]:
    """Smallest bin that holds an object of the given size, in grid units.

    Args:
        length_mm, width_mm, height_mm: the object's bounding box
        clearance: slack added around the object before rounding up, per side

    Returns:
        ``{"cols", "rows", "height_u"}``. The height allows for the standard 7 mm solid
        base under the cavity, so the object clears the floor.
    """
    # A bin's usable span is 42 * u - 0.5 - 2 * wall, so the walls and the inter-bin gap
    # are paid once for the whole bin, not once per unit.
    overhead = GRID_CLEARANCE_MM + 2 * WALL_MM
    cols = max(1, math.ceil((length_mm + 2 * clearance + overhead) / GRID_PITCH_MM))
    rows = max(1, math.ceil((width_mm + 2 * clearance + overhead) / GRID_PITCH_MM))
    height_u = max(2, math.ceil((height_mm + clearance + BASE_HEIGHT_MM) / HEIGHT_UNIT_MM))
    return {"cols": cols, "rows": rows, "height_u": height_u}
