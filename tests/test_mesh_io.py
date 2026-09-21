import numpy as np
import pytest
import trimesh

import mesh_io


def _downward_tri(gamma_deg):
    """A single downward-facing triangle (area 0.5) whose overhang angle from
    horizontal is 90 - gamma_deg. Smaller gamma => steeper (nearer-horizontal)."""
    g = np.radians(gamma_deg)
    verts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, -np.cos(g), -np.sin(g)]])
    return trimesh.Trimesh(vertices=verts, faces=[[0, 1, 2]], process=False)


def test_support_cost_weights_steeper_overhangs_more():
    # Equal area; the steeper (near-horizontal, angle 80) face costs more than the
    # one just past the limit (angle 50).
    steep = mesh_io.support_cost(_downward_tri(10.0), 45.0, 2.0)  # angle 80
    shallow = mesh_io.support_cost(_downward_tri(40.0), 45.0, 2.0)  # angle 50
    assert steep > shallow > 0.0


def test_support_cost_zero_at_or_under_limit():
    # angle 40 <= 45 limit -> not an unsupported overhang -> zero cost.
    assert mesh_io.support_cost(_downward_tri(50.0), 45.0, 2.0) == 0.0


def test_support_cost_excludes_masked_faces():
    tri = _downward_tri(10.0)
    assert mesh_io.support_cost(tri, 45.0, 2.0) > 0.0
    excluded = np.array([True])
    assert mesh_io.support_cost(tri, 45.0, 2.0, exclude_mask=excluded) == 0.0


def test_overhang_metrics_excludes_bed_bottom():
    # A cube's flat bottom face (normal -Z, 90 deg from horizontal) rests on the bed
    # (it is at the mesh's lowest level), so it is not an unsupported overhang; the
    # cube has no other downward faces, so nothing is flagged.
    box = trimesh.creation.box([10.0, 10.0, 10.0])
    m = mesh_io.overhang_metrics(box, 45.0)
    assert m["worst_angle_deg"] is None
    assert m["overhang_area_mm2"] == 0.0


def test_overhang_metrics_flags_elevated_downface():
    # A downward face elevated above the mesh's lowest point IS a real overhang: the
    # flat down-face at Z=5 sits well above the lowest vertex (Z=0), so it is flagged.
    verts = np.array(
        [[0, 0, 5], [0, 10, 5], [10, 0, 5], [100, 0, 0], [100, 10, 0], [108.66, 0, 5]],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    m = mesh_io.overhang_metrics(mesh, 45.0)
    assert m["worst_angle_deg"] == pytest.approx(90.0, abs=1e-3)
    assert m["overhang_area_mm2"] > 0.0


def _tilted_plane(width, depth, tilt_deg, down=False):
    """A flat width x depth plane tilted `tilt_deg` about X. Up-facing unless `down`.

    Wound so the outward normal is +Z before the tilt (so nz = cos(tilt) after, an
    up-facing slope inclined `tilt_deg` from horizontal); `down` reverses the winding.
    """
    from trimesh.transformations import rotation_matrix

    v = np.array([[0, 0, 0], [width, 0, 0], [width, depth, 0], [0, depth, 0]], dtype=float)
    faces = np.array([[0, 2, 1], [0, 3, 2]]) if down else np.array([[0, 1, 2], [0, 2, 3]])
    m = trimesh.Trimesh(vertices=v, faces=faces, process=False)
    m.apply_transform(rotation_matrix(np.radians(tilt_deg), [1, 0, 0]))
    return m


def test_up_facing_incline_area_counts_shallow_up_ramp():
    # A 100 mm^2 up-facing plane inclined 30 deg is in the (5, 45) band; area is preserved.
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 30), 5, 45) == 100.0


def test_up_facing_incline_area_excludes_down_facing():
    # Same 30 deg slope facing DOWN is an overhang concern, not a cosmetic up-slope.
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 30, down=True), 5, 45) == 0.0


def test_up_facing_incline_area_excludes_flat_and_vertical():
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 0), 5, 45) == 0.0  # flat top
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 90), 5, 45) == 0.0  # wall


def test_up_facing_incline_area_band_is_open_interval():
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 3), 5, 45) == 0.0  # below 5
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 60), 5, 45) == 0.0  # above 45
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 45), 5, 45) == 0.0  # 45 excluded
    assert mesh_io.up_facing_incline_area(_tilted_plane(10, 10, 44), 5, 45) == 100.0  # just inside


def test_load_mesh_valid(tmp_stl):
    tm = mesh_io.load_mesh(str(tmp_stl))
    assert len(tm.vertices) > 0
    assert len(tm.faces) > 0
    assert tm.is_watertight


def test_load_mesh_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Failed to load STL"):
        mesh_io.load_mesh(str(tmp_path / "nope.stl"))


def test_load_mesh_empty_file(tmp_path):
    empty = tmp_path / "empty.stl"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        mesh_io.load_mesh(str(empty))


def test_load_mesh_no_pyrender_import():
    """mesh_io must not pull in pyrender (it's the whole point of the split)."""
    assert "pyrender" not in dir(mesh_io), "mesh_io should not reference pyrender"


def _slab_on_pillars(gap, overhang_right=None):
    """Base plate with two pillars and a slab across them (a bridge over `gap` mm).

    With `overhang_right` set, a single pillar carries a slab that projects that far
    beyond it (a one-sided cantilever ledge) instead.
    """
    box = trimesh.creation.box
    base = box([60.0, 20.0, 2.0])
    base.apply_translation([30.0, 10.0, 1.0])
    parts = [base]
    if overhang_right is None:
        for x0, x1 in ((0.0, 10.0), (10.0 + gap, 20.0 + gap)):
            p = box([x1 - x0, 20.0, 10.0])
            p.apply_translation([(x0 + x1) / 2, 10.0, 7.0])
            parts.append(p)
        x_end = 20.0 + gap
    else:
        p = box([10.0, 20.0, 10.0])
        p.apply_translation([5.0, 10.0, 7.0])
        parts.append(p)
        x_end = 10.0 + overhang_right
    slab = box([x_end, 20.0, 2.0])
    slab.apply_translation([x_end / 2, 10.0, 13.0])
    parts.append(slab)
    return trimesh.boolean.union(parts, engine="manifold")


def test_short_supported_ceiling_is_a_bridge():
    m = mesh_io.overhang_metrics(_slab_on_pillars(6.0), 45.0, bridge_max_mm=10.0)
    assert m["overhang_area_mm2"] == 0.0
    assert m["bridge_count"] == 1
    assert m["bridge_area_mm2"] == pytest.approx(6.0 * 20.0, rel=1e-3)


def test_long_span_is_an_overhang():
    m = mesh_io.overhang_metrics(_slab_on_pillars(25.0), 45.0, bridge_max_mm=10.0)
    assert m["bridge_count"] == 0
    assert m["overhang_area_mm2"] == pytest.approx(25.0 * 20.0, rel=1e-3)


def test_short_one_sided_ledge_is_an_overhang():
    m = mesh_io.overhang_metrics(_slab_on_pillars(0.0, overhang_right=6.0), 45.0)
    assert m["bridge_count"] == 0
    assert m["overhang_area_mm2"] == pytest.approx(6.0 * 20.0, rel=1e-3)


def test_bridge_cost_is_discounted():
    mesh = _slab_on_pillars(6.0)
    bed = mesh_io.bed_contact_mask(mesh)
    bridge = mesh_io.support_cost(mesh, 45.0, 2.0, bed)
    span = mesh_io.support_cost(mesh, 45.0, 2.0, bed, bridge_max_mm=0.0)
    assert 0.0 < bridge == pytest.approx(span * mesh_io.BRIDGE_COST_FACTOR, rel=1e-3)


def test_overhang_area_independent_of_tessellation():
    mesh = _slab_on_pillars(0.0, overhang_right=30.0)
    fine = mesh.subdivide().subdivide()
    a = mesh_io.overhang_metrics(mesh, 45.0)["overhang_area_mm2"]
    b = mesh_io.overhang_metrics(fine, 45.0)["overhang_area_mm2"]
    assert b == pytest.approx(a, rel=0.01)


def test_support_cost_has_no_cliff_at_limit():
    below = mesh_io.support_cost(_downward_tri(90.0 - 44.9), 45.0, 2.0)
    above = mesh_io.support_cost(_downward_tri(90.0 - 45.1), 45.0, 2.0)
    assert below == 0.0
    assert above < 1e-3
