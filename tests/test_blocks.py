# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Integration tests for the blocks library.

Each block is called with valid params and the result is checked to be
a CadQuery Workplane containing at least one solid.
"""

import cadquery as cq
import pytest

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
    pcb_standoff,
    screw_boss,
    snap_hook_clip,
    snap_socket_receiver,
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
from blocks.primitives import fillet_box, hollow_box
from blocks.validate import get_block_names, load_inventory, validate_inventory


def _is_solid(result) -> bool:
    return isinstance(result, cq.Workplane) and len(result.solids().vals()) > 0


# ---- primitives ----


def test_fillet_box():
    r = fillet_box(50, 30, 20, r=2)
    assert _is_solid(r)


def test_hollow_box():
    r = hollow_box(50, 30, 20, wall=2, floor_t=1.5, corner_r=2)
    assert _is_solid(r)


def test_hollow_box_no_fillet():
    r = hollow_box(40, 25, 15, wall=2, floor_t=1.5)
    assert _is_solid(r)


# ---- fasteners ----


def test_screw_boss():
    r = screw_boss(d_screw=2.5, d_outer=6, h=4)
    assert _is_solid(r)


def test_pcb_standoff():
    r = pcb_standoff(d_screw=2.7, d_outer=6, h=5)
    assert _is_solid(r)


def test_snap_hook_clip():
    r = snap_hook_clip(w=6, length=12, h=2, hook_h=1.5)
    assert _is_solid(r)


def test_snap_socket_receiver():
    r = snap_socket_receiver(w=6.2, h=1.8, depth=2)
    assert _is_solid(r)


def test_alignment_pin():
    r = alignment_pin(d=3, h=4)
    assert _is_solid(r)


def test_alignment_socket():
    r = alignment_socket(d=3, h=4, clearance=0.2)
    assert _is_solid(r)


# ---- connectors ----


def test_port_cutout():
    r = port_cutout(w=9.0, h=3.5, depth=2.0)
    assert _is_solid(r)


def test_port_cutout_no_chamfer():
    r = port_cutout(w=12, h=6, depth=2, chamfer=0)
    assert _is_solid(r)


def test_cable_slot():
    r = cable_slot(w=8, h=4, depth=2.0)
    assert _is_solid(r)


def test_vent_grid():
    r = vent_grid(cols=3, rows=2, slot_w=4, slot_l=12, spacing=2, depth=2)
    assert _is_solid(r)


def test_vent_grid_single():
    r = vent_grid(cols=1, rows=1, slot_w=10, slot_l=20, spacing=2, depth=2)
    assert _is_solid(r)


# ---- teardrop bore ----


def test_teardrop_bore_solid_and_watertight():
    r = teardrop_bore(d=8.0, depth=4.0)
    assert _is_solid(r) and len(r.solids().vals()) == 1
    assert r.val().isValid()


def test_teardrop_bore_as_cut_watertight():
    wall = cq.Workplane("XY").box(20, 4.0, 20)
    res = wall.cut(teardrop_bore(d=8.0, depth=4.0))
    assert _is_solid(res) and len(res.solids().vals()) == 1
    assert res.val().isValid()


def test_teardrop_bore_dimensions_and_epsilon():
    r = teardrop_bore(d=8.0, depth=4.0)
    bb = _bb(r)
    assert abs(bb.xlen - 8.0) < 1e-3  # circular portion diameter, unaffected by eps
    assert abs(bb.ylen - (4.0 + 1e-4)) < 1e-6  # extrusion overcut by _EPS


def test_teardrop_bore_upper_profile_is_a_peak():
    d, r = 8.0, 4.0
    bore = teardrop_bore(d=d, depth=4.0)
    bb = _bb(bore)
    # apex sits at max Z, one radius above center for the default 45 deg roof
    assert abs(bb.zmax - r) < 1e-3
    assert abs(bb.zmin + r) < 1e-3
    # just below the apex the section is a narrow peak, not a wide circular arc:
    # a plain circle of this radius would be ~2.4 mm wide here.
    slab = cq.Workplane("XY").transformed(offset=(0, 2.0, 3.85)).box(20, 4.1, 0.1)
    top_band = bore.intersect(slab)
    assert _bb(top_band).xlen < 1.0


def test_teardrop_bore_roof_within_overhang_limit():
    import math

    bore = teardrop_bore(d=8.0, depth=4.0, angle=45.0)
    roof_angles = []
    for f in bore.faces().vals():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt()
        if abs(n.z) < 1e-3 or abs(n.x) < 1e-3:
            continue  # skip the +/-Y end caps (normal along Y)
        # angle of the face normal from the Z axis == face angle from horizontal
        roof_angles.append(math.degrees(math.acos(min(1.0, abs(n.z)))))
    assert len(roof_angles) == 2
    for a in roof_angles:
        assert a <= 45.0 + 1e-3


# ---- teardrop post ----


def test_teardrop_post_solid_and_watertight():
    r = teardrop_post(d=8.0, length=6.0)
    assert _is_solid(r) and len(r.solids().vals()) == 1
    assert r.val().isValid()


def test_teardrop_post_union_watertight():
    wall = cq.Workplane("XY").box(20, 2.0, 20)
    res = wall.union(teardrop_post(d=8.0, length=6.0))
    assert _is_solid(res)
    assert res.val().isValid()


def test_teardrop_post_dimensions():
    r = teardrop_post(d=8.0, length=6.0)
    bb = _bb(r)
    assert abs(bb.xlen - 8.0) < 1e-3  # circular portion diameter
    assert abs(bb.ylen - 6.0) < 1e-3  # extrusion length along the axis


def test_teardrop_post_flat_bottom_at_min_z():
    import math

    d, r, flat = 8.0, 4.0, 1.2
    post = teardrop_post(d=d, length=6.0, flat=flat)
    bb = _bb(post)
    # arc top one radius up; flat bottom at -(r - flat/2)*tan(45) below center
    z_flat = -(r - flat / 2.0) * math.tan(math.radians(45.0))
    assert abs(bb.zmax - r) < 1e-3
    assert abs(bb.zmin - z_flat) < 1e-3
    # the bottom is a narrow flat, not a wide circular arc
    slab = cq.Workplane("XY").transformed(offset=(0, 3.0, z_flat + 0.05)).box(20, 6.1, 0.1)
    assert _bb(post.intersect(slab)).xlen < 2.0


def test_teardrop_post_underside_within_overhang_limit():
    import math

    post = teardrop_post(d=8.0, length=6.0, angle=45.0)
    face_angles = []
    for f in post.faces().vals():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt()
        if abs(n.z) < 1e-3 or abs(n.x) < 1e-3:
            continue  # skip +/-Y end caps and the horizontal flat bottom
        face_angles.append(math.degrees(math.acos(min(1.0, abs(n.z)))))
    assert len(face_angles) == 2
    for a in face_angles:
        assert a <= 45.0 + 1e-3


def test_teardrop_post_small_d_warns_and_builds():
    with pytest.warns(UserWarning):
        r = teardrop_post(d=2.0, length=4.0)
    assert _is_solid(r) and len(r.solids().vals()) == 1
    assert r.val().isValid()


def test_teardrop_post_oversized_flat_clamped():
    with pytest.warns(UserWarning):
        r = teardrop_post(d=4.0, length=4.0, flat=5.0)
    assert _is_solid(r) and len(r.solids().vals()) == 1
    assert r.val().isValid()


# ---- counterbore / countersink / nut trap ----


def test_counterbore_hole():
    r = counterbore_hole(d_screw=3.4, d_head=5.5, h_head=3.0, depth=10.0)
    assert _is_solid(r)
    bb = r.val().BoundingBox()
    assert abs(bb.zlen - 10.0) < 0.1


def test_counterbore_hole_as_cut():
    slab = cq.Workplane("XY").box(20, 20, 10)
    r = slab.cut(counterbore_hole(3.4, 5.5, 3.0, 10.0))
    assert _is_solid(r)


def test_countersink_hole():
    r = countersink_hole(d_screw=3.2, d_sink=6.0, depth=10.0)
    assert _is_solid(r)


def test_countersink_hole_as_cut():
    slab = cq.Workplane("XY").box(20, 20, 10)
    r = slab.cut(countersink_hole(3.2, 6.0, 10.0))
    assert _is_solid(r)


def test_hex_nut_trap_no_screw():
    r = hex_nut_trap(nut_flat=5.5, nut_h=2.4, depth=3.0)
    assert _is_solid(r)
    bb = r.val().BoundingBox()
    assert abs(bb.zlen - 3.0) < 0.1


def test_hex_nut_trap_with_screw():
    r = hex_nut_trap(nut_flat=5.5, nut_h=2.4, depth=8.0, d_screw=3.4)
    assert _is_solid(r)
    bb = r.val().BoundingBox()
    assert abs(bb.zlen - 8.0) < 0.1


def test_hex_nut_trap_as_cut():
    wall = cq.Workplane("XY").box(20, 20, 10)
    r = wall.cut(hex_nut_trap(5.5, 2.4, 10.0, d_screw=3.4))
    assert _is_solid(r)


# ---- hardware (cq_warehouse-backed) ----


def test_heat_set_boss_m3():
    r = heat_set_boss(size="M3-0.5-6", d_outer=7, h=8)
    assert _is_solid(r)


def test_heat_set_boss_m4():
    r = heat_set_boss(size="M4-0.7-8", d_outer=9, h=10)
    assert _is_solid(r)


def test_socket_head_cap_screw():
    r = socket_head_cap_screw(size="M3-0.5", length=12)
    assert _is_solid(r)


def test_hex_head_screw():
    r = hex_head_screw(size="M4-0.7", length=20)
    assert _is_solid(r)


def test_hex_nut():
    r = hex_nut(size="M3-0.5")
    assert _is_solid(r)


# ---- inventory validation ----


def test_inventory_loads():
    inv = load_inventory()
    assert len(inv) >= 11


def test_inventory_valid():
    inv = load_inventory()
    errors = validate_inventory(inv)
    assert errors == [], f"Inventory errors: {errors}"


def test_inventory_has_all_required_blocks():
    names = get_block_names()
    required = {
        "fillet_box",
        "hollow_box",
        "screw_boss",
        "pcb_standoff",
        "snap_hook_clip",
        "snap_socket_receiver",
        "alignment_pin",
        "alignment_socket",
        "port_cutout",
        "cable_slot",
        "vent_grid",
        "teardrop_bore",
    }
    missing = required - names
    assert not missing, f"Missing blocks in inventory: {missing}"


def test_teardrop_bore_descriptor():
    inv = {b["name"]: b for b in load_inventory()}
    desc = inv["teardrop_bore"]
    assert desc["module"] == "blocks.connectors"
    assert {"d", "depth", "angle"} <= set(desc["params"])
    assert any(i["type"] == "axis" for i in desc["interfaces"])


def test_teardrop_bore_top_level_import():
    from blocks import teardrop_bore as tb

    assert callable(tb)


def test_teardrop_post_descriptor():
    inv = {b["name"]: b for b in load_inventory()}
    desc = inv["teardrop_post"]
    assert desc["module"] == "blocks.connectors"
    assert {"d", "length", "angle", "flat"} <= set(desc["params"])
    assert any(i["type"] == "axis" for i in desc["interfaces"])


def test_teardrop_post_top_level_import():
    from blocks import teardrop_post as tp

    assert callable(tp)


# ---- __init__ re-exports ----


def test_top_level_import():
    from blocks import (
        fillet_box,
        vent_grid,
    )

    assert callable(fillet_box)
    assert callable(vent_grid)


# ---- joints ----


def _bb(r):
    return r.val().BoundingBox()


def _overlap_solids(a, b) -> int:
    return len(a.intersect(b).solids().vals())


# dovetail (regression after extrude-core refactor)


def test_dovetail_groove_geometry():
    g = dovetail_groove(width=26, wall=3, depth=2, length=30)
    bb = _bb(g)
    assert abs(bb.zmin - 0) < 1e-3 and abs(bb.zmax - 2) < 1e-3
    assert abs(bb.xmin + bb.xmax) < 1e-6  # symmetric about X=0
    # base width = inner + 2*flare, flare = tan(35deg)*2
    import math

    expected = (26 - 6) + 2 * math.tan(math.radians(35)) * 2
    assert abs(bb.xlen - expected) < 1e-2


def test_dovetail_tongue_smaller_by_clearance():
    g = dovetail_groove(26, 3, 2, 30)
    t = dovetail_tongue(26, 3, 2, 30, clearance=0.1)
    assert abs(_bb(g).xlen - _bb(t).xlen - 0.2) < 1e-3
    assert abs(_bb(t).zlen - 2.0) < 1e-3


# finger joint


def test_finger_joint_complementary_disjoint():
    a = finger_joint(width=24, thickness=3, fingers=6, length=10, start_high=True)
    b = finger_joint(width=24, thickness=3, fingers=6, length=10, start_high=False)
    assert _is_solid(a) and _is_solid(b)
    assert _overlap_solids(a, b) == 0
    # union spans (nearly) the full width
    union = a.union(b)
    assert _bb(union).xlen > 24 - 2 * 0.1 - 1e-6


def test_finger_joint_dimensions():
    a = finger_joint(width=24, thickness=3, fingers=6, length=10)
    bb = _bb(a)
    assert abs(bb.zlen - 3) < 1e-3 and abs(bb.ylen - 10) < 1e-3


def test_finger_joint_clearance_shrinks_finger():
    tight = finger_joint(24, 3, 6, 10, clearance=0.0)
    loose = finger_joint(24, 3, 6, 10, clearance=0.1)
    # each of 3 fingers narrower by 2*0.1 -> overall span narrower by 0.2
    assert _bb(tight).xlen - _bb(loose).xlen > 0.15


# mortise & tenon


def test_tenon_dimensions():
    t = tenon(w=8, h=4, length=10)
    bb = _bb(t)
    assert abs(bb.xlen - 8) < 1e-3 and abs(bb.ylen - 4) < 1e-3
    assert abs(bb.zlen - 10) < 1e-3


def test_mortise_exceeds_tenon_by_clearance():
    t = tenon(8, 4, 10)
    m = mortise(8, 4, 10, clearance=0.2)
    assert abs(_bb(m).xlen - _bb(t).xlen - 0.4) < 1e-3
    assert abs(_bb(m).ylen - _bb(t).ylen - 0.4) < 1e-3


# dowel pin & bore


def test_dowel_pin_dimensions():
    p = dowel_pin(d=4, length=12)
    bb = _bb(p)
    assert abs(bb.xlen - 4) < 1e-3 and abs(bb.zlen - 12) < 1e-3


def test_dowel_bore_fit_by_clearance_sign():
    slip = dowel_bore(4, 12, clearance=0.1)
    press = dowel_bore(4, 12, clearance=-0.1)
    assert abs(_bb(slip).xlen - 4.2) < 1e-3
    assert abs(_bb(press).xlen - 3.8) < 1e-3


# ball joint


def test_ball_stud_geometry():
    s = ball_stud(d_ball=10, d_stem=5, stem_l=8, fillet=2)
    bb = _bb(s)
    assert abs(bb.xlen - 10) < 1e-2  # max cross-section = ball diameter
    assert bb.zlen >= 8 + 10 - 1e-3  # ball sits above the stem


def test_ball_socket_retains_and_slotted():
    import math

    d_ball, ra, slot_w, wall, clr = 10, 30, 2, 2, 0.2
    so = ball_socket(d_ball, ra, slot_w, wall, clr)
    assert _is_solid(so) and len(so.solids().vals()) == 1

    r_cav = (d_ball + 2 * clr) / 2
    center_z = wall + r_cav
    rim_z = center_z + r_cav * math.sin(math.radians(ra))

    # retention: a column the width of the ball is blocked by the lip above the equator
    probe = (
        cq.Workplane("XY")
        .transformed(offset=(0, 0, center_z))
        .circle(d_ball / 2)
        .extrude(rim_z - center_z + 2)
    )
    assert len(so.intersect(probe).solids().vals()) > 0

    # flex slot splits the retaining lip ring into two arcs
    z_mid = (center_z + rim_z) / 2
    span = 2 * (r_cav + wall) + 2
    slab = cq.Workplane("XY").transformed(offset=(0, 0, z_mid)).box(span, span, 0.05)
    assert len(so.intersect(slab).solids().vals()) == 2


# pin hinge (matched-pair block: returns two named leaf member unions)


def test_pin_hinge_returns_two_named_leaves():
    h = pin_hinge(length=30, knuckles=5, leaf_w=10, leaf_t=2)
    assert set(h.keys()) == {"leaf_a", "leaf_b"}
    a, b = h["leaf_a"], h["leaf_b"]
    # each leaf is its own watertight body; they do not overlap
    assert _is_solid(a) and _is_solid(b)
    assert _overlap_solids(a, b) == 0
    # leaves lie on opposite sides of the pin axis (X=0)
    assert _bb(a).xmin < 0 and _bb(b).xmax > 0


def test_pin_hinge_each_leaf_coaxial_bore():
    h = pin_hinge(length=30, knuckles=5, leaf_w=10, leaf_t=2, d_filament=1.9)
    # a 1.9 mm rod along the axis sits in the bore void of BOTH leaves (no intersection)
    d_outer = 1.9 + 2.0
    rod = cq.Workplane("XY").add(
        cq.Solid.makeCylinder(
            1.9 / 2 - 0.05, 30, pnt=cq.Vector(0, 0, d_outer / 2), dir=cq.Vector(0, 1, 0)
        )
    )
    for leaf in h.values():
        assert len(leaf.intersect(rod).solids().vals()) == 0


def test_pin_hinge_clearance_separates_knuckles():
    def total_volume(hinge):
        return sum(leaf.val().Volume() for leaf in hinge.values())

    snug = pin_hinge(30, 5, 10, 2, clearance=0.1)
    loose = pin_hinge(30, 5, 10, 2, clearance=0.6)
    # wider axial clearance removes more knuckle material
    assert total_volume(loose) < total_volume(snug)


# living hinge


def test_living_hinge_solid_and_watertight():
    h = living_hinge(length=40, panel_w=20, panel_t=3, web_t=0.6, web_w=2.0)
    assert _is_solid(h) and len(h.solids().vals()) == 1
    assert h.val().isValid()


def test_living_hinge_web_thinner_than_panels():
    h = living_hinge(length=40, panel_w=20, panel_t=3, web_t=0.6, web_w=2.0)
    # the central web zone is only web_t tall, the panels are panel_t tall
    web_slab = cq.Workplane("XY").box(1.0, 50, 10).translate((0, 0, 0))
    web_z = _bb(h.intersect(web_slab)).zlen
    assert abs(web_z - 0.6) < 1e-3
    assert abs(_bb(h).zlen - 3.0) < 1e-3


def test_living_hinge_web_spans_full_length():
    h = living_hinge(length=40, panel_w=20, panel_t=3)
    assert abs(_bb(h).ylen - 40) < 1e-3


# shadow gap


def test_shadow_gap_dimensions():
    lip = shadow_gap(length=50, wall=1.6, overlap=3.0)
    assert _is_solid(lip) and len(lip.solids().vals()) == 1
    bb = _bb(lip)
    assert abs(bb.xlen - 50) < 1e-3  # seam length (X)
    assert abs(bb.zlen - 1.6) < 1e-3  # lip thickness (Z)
    assert abs(bb.ymin - 0) < 1e-3 and abs(bb.ymax - 3.0) < 1e-3  # projects Y=0..overlap


def test_shadow_gap_union_watertight():
    panel = cq.Workplane("XY").box(50, 4, 20)
    res = panel.union(shadow_gap(length=50, wall=1.6, overlap=3.0))
    assert _is_solid(res)
    assert res.val().isValid()


def test_shadow_gap_descriptor():
    inv = {b["name"]: b for b in load_inventory()}
    desc = inv["shadow_gap"]
    assert desc["module"] == "blocks.joints"
    assert desc["motion"] == "rigid" and desc["reversible"] is True
    assert any(i["type"] == "seam" for i in desc["interfaces"])


def test_flex_blocks_top_level_import():
    from blocks import living_hinge as lh
    from blocks import pin_hinge as fh
    from blocks import shadow_gap as sg

    assert callable(fh) and callable(lh) and callable(sg)


# ---- interface vocabulary ----


def _block_with_interface(itype):
    return {
        "name": "iface_fixture",
        "module": "blocks.primitives",
        "function": "fillet_box",
        "use": "interface vocabulary fixture",
        "params": {},
        "dimensions": [1, 1, 1],
        "interfaces": [{"type": itype, "orientation": "+Z", "origin": [0, 0, 0]}],
    }


def test_union_interface_type_accepted():
    """A block declaring a `union` interface (fused into the parent body) validates."""
    errors = validate_inventory([_block_with_interface("union")])
    assert errors == [], errors


def test_unknown_interface_type_still_rejected():
    errors = validate_inventory([_block_with_interface("glue_tab")])
    assert any("glue_tab" in e and "allowed vocabulary" in e for e in errors)


def test_shipped_inventory_still_valid():
    """Regression guard: adding `union` to the vocabulary keeps inventory.json valid."""
    assert validate_inventory(load_inventory()) == []


def test_joint_axis_interface_type_accepted():
    """A block declaring the motion-agnostic `joint_axis` kinematic reference validates."""
    errors = validate_inventory([_block_with_interface("joint_axis")])
    assert errors == [], errors


def test_retired_hinge_axis_interface_type_rejected():
    """`hinge_axis` was generalized to `joint_axis` and is no longer a known type."""
    errors = validate_inventory([_block_with_interface("hinge_axis")])
    assert any("hinge_axis" in e and "allowed vocabulary" in e for e in errors)


def test_shipped_inventory_declares_no_hinge_axis():
    """No shipped block still declares the retired `hinge_axis` interface type."""
    inv = load_inventory()
    offenders = [
        block["name"]
        for block in inv
        for iface in block.get("interfaces") or []
        if iface.get("type") == "hinge_axis"
    ]
    assert offenders == [], offenders


# ---- matched-pair block emits ----


def _block_with_emits(emits):
    return {
        "name": "emits_fixture",
        "module": "blocks.primitives",
        "function": "fillet_box",
        "use": "matched-pair emits fixture",
        "params": {},
        "dimensions": [1, 1, 1],
        "interfaces": [],
        "emits": emits,
    }


def test_pin_hinge_declares_emits():
    """pin_hinge's inventory descriptor names its two member ids."""
    inv = load_inventory()
    pin_hinge = next(b for b in inv if b["name"] == "pin_hinge")
    assert pin_hinge["emits"] == ["leaf_a", "leaf_b"]


def test_emits_of_two_strings_accepted():
    errors = validate_inventory([_block_with_emits(["leaf_a", "leaf_b"])])
    assert errors == [], errors


def test_emits_of_wrong_length_rejected():
    errors = validate_inventory([_block_with_emits(["leaf_a"])])
    assert any("emits must be a list of exactly two strings" in e for e in errors)


def test_emits_of_non_strings_rejected():
    errors = validate_inventory([_block_with_emits(["leaf_a", 2])])
    assert any("emits must be a list of exactly two strings" in e for e in errors)
