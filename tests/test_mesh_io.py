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
    with pytest.raises(ValueError, match="STL not found"):
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


def test_lateral_area_matches_prismatic_box_perimeter():
    box = trimesh.creation.box([30.0, 30.0, 60.0])
    lateral = mesh_io.lateral_area(box)
    expected = 2 * (30.0 * 60.0) + 2 * (30.0 * 60.0)  # 4 walls, 30x60 each
    assert lateral == pytest.approx(expected, rel=1e-6)
    height = box.bounds[1][2] - box.bounds[0][2]
    mean_perimeter = lateral / height
    assert mean_perimeter == pytest.approx(4 * 30.0, rel=1e-6)


def test_lateral_area_excludes_flat_top_and_bottom():
    box = trimesh.creation.box([10.0, 10.0, 10.0])
    total = float(box.area_faces.sum())
    lateral = mesh_io.lateral_area(box)
    assert lateral < total
    assert lateral == pytest.approx(4 * 10.0 * 10.0, rel=1e-6)


def _wedge(interior_deg, dx=0.0, seam_pts=2):
    """Two triangle strips hinged on a shared seam along +X: interior dihedral
    `interior_deg` between the two sides (0 = a fin folded flat onto itself)."""
    c, s = np.cos(np.radians(interior_deg)), np.sin(np.radians(interior_deg))
    seam = [[dx + i, 0.0, 0.0] for i in range(seam_pts)]
    verts = list(seam)
    faces = []
    for i in range(seam_pts - 1):
        a = len(verts)
        verts += [[dx + i, 1.0, 0.0], [dx + i, c, s]]  # flat-side apex, tilted-side apex
        faces += [[i, i + 1, a], [i + 1, i, a + 1]]
    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


def test_fold_metrics_flags_zero_thickness_fin():
    r = mesh_io.fold_metrics(_wedge(2.0))
    assert r["count"] == 1
    assert r["sharpest_deg"] == pytest.approx(2.0, abs=1e-6)
    assert r["clusters"][0]["location_xyz_mm"] == pytest.approx([0.5, 0.0, 0.0], abs=1e-6)


def test_fold_metrics_ignores_ordinary_corners_and_curves():
    for m in (
        trimesh.creation.box([10.0, 10.0, 10.0]),
        trimesh.creation.cylinder(radius=5.0, height=10.0, sections=64),
    ):
        assert mesh_io.fold_metrics(m)["count"] == 0


def test_fold_metrics_ignores_deliberate_wedge_tip():
    # A ~20 deg taper is a legitimate feature, not a fin.
    assert mesh_io.fold_metrics(_wedge(20.0))["count"] == 0


def test_fold_metrics_one_fin_along_a_seam_is_one_cluster():
    r = mesh_io.fold_metrics(_wedge(2.0, seam_pts=5))  # 4 fold pairs sharing seam vertices
    assert r["count"] == 1


def test_fold_metrics_separate_fins_are_separate_clusters():
    two = trimesh.util.concatenate([_wedge(2.0), _wedge(5.0, dx=20.0)])
    r = mesh_io.fold_metrics(two)
    assert r["count"] == 2
    assert [c["angle_deg"] for c in r["clusters"]] == pytest.approx([2.0, 5.0], abs=1e-6)


def test_overhang_regions_read_vertices_once_regardless_of_region_count(monkeypatch):
    # Many disconnected downward triangles -> many regions; vertex reads must not scale.
    orig = trimesh.Trimesh.__dict__["vertices"]
    reads = [0]

    def counted(self):
        reads[0] += 1
        return orig.fget(self)

    monkeypatch.setattr(trimesh.Trimesh, "vertices", property(counted, orig.fset))

    def reads_for(n):
        verts = np.array(
            [[[3 * i, 0, 0], [3 * i + 1, 0, 0], [3 * i, -1, -0.001]] for i in range(n)]
        )
        faces = np.arange(3 * n).reshape(n, 3)
        mesh = trimesh.Trimesh(vertices=verts.reshape(-1, 3), faces=faces, process=False)
        reads[0] = 0
        assert len(mesh_io.overhang_regions(mesh, 45.0)) == n
        return reads[0]

    assert reads_for(50) == reads_for(5)


def _reference_is_bridge(mesh, faces, in_region, angles, bridge_max_mm, ctx):
    """Per-edge Python implementation of `mesh_io._is_bridge` (pre-vectorization behavior)."""
    if "lookup" not in ctx:
        adj_edges = np.sort(mesh.face_adjacency_edges, axis=1)
        ctx["lookup"] = {
            tuple(e): (int(f[0]), int(f[1]))
            for e, f in zip(adj_edges, mesh.face_adjacency, strict=True)
        }
    verts, lookup = np.asarray(mesh.vertices), ctx["lookup"]
    centroids_z = mesh.triangles.mean(axis=1)[:, 2]
    area = np.asarray(mesh.area_faces)
    if np.average(angles[faces], weights=area[faces]) < mesh_io.BRIDGE_MIN_DEG:
        return False
    tri = np.asarray(mesh.faces)[faces]
    pts = verts[np.unique(tri)][:, :2]
    if len(pts) < 3:
        return False
    to_rect, rect = trimesh.bounds.oriented_bounds_2D(pts)
    short = float(rect.min())
    if short > bridge_max_mm or short <= 0.0:
        return False
    edges = np.sort(tri[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    owner = np.repeat(faces, 3)
    _, inv, cnt = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    boundary = cnt[inv.reshape(-1)] == 1
    side_len = [rect[1], rect[1], rect[0], rect[0]]
    covered = np.zeros(4)
    for e, f, is_b in zip(edges, owner, boundary, strict=True):
        if not is_b:
            continue
        pair = lookup.get(tuple(e))
        if pair is None:
            continue
        other = pair[1] if pair[0] == f else pair[0]
        if in_region[other]:
            continue
        mid = verts[e].mean(axis=0)
        if centroids_z[other] >= mid[2] - 1e-6:
            continue
        x, y, _ = to_rect @ np.array([mid[0], mid[1], 1.0])
        if abs(x) / (rect[0] / 2) >= abs(y) / (rect[1] / 2):
            side = 0 if x > 0 else 1
        else:
            side = 2 if y > 0 else 3
        covered[side] += np.linalg.norm(verts[e[0]] - verts[e[1]])
    supported = sum(
        1 for c, n in zip(covered, side_len, strict=True) if c >= mesh_io.BRIDGE_SIDE_COVERAGE * n
    )
    return supported >= 2


def _two_bridges_and_ledge():
    """Disjoint copies of a bridge, a long span and a ledge, so one mesh has several regions."""
    parts = []
    for i, m in enumerate((_slab_on_pillars(6.0), _slab_on_pillars(25.0), _slab_on_pillars(6.0))):
        m = m.copy()
        m.apply_translation([0.0, 40.0 * i, 0.0])
        parts.append(m)
    return trimesh.util.concatenate(parts)


@pytest.mark.parametrize(
    "make_mesh",
    [
        lambda: _slab_on_pillars(6.0),
        lambda: _slab_on_pillars(25.0),
        lambda: _slab_on_pillars(0.0, overhang_right=6.0),
        lambda: _slab_on_pillars(6.0).subdivide(),
        _two_bridges_and_ledge,
    ],
    ids=["bridge", "long-span", "ledge", "subdivided-bridge", "multi-region"],
)
def test_vectorized_bridge_matches_per_edge_reference(make_mesh, monkeypatch):
    mesh = make_mesh()
    new_regions = mesh_io.overhang_regions(mesh, 45.0, bridge_max_mm=10.0)
    new_cost = mesh_io.support_cost(mesh, 45.0, 2.0, bridge_max_mm=10.0)
    monkeypatch.setattr(mesh_io, "_is_bridge", _reference_is_bridge)
    old_regions = mesh_io.overhang_regions(mesh, 45.0, bridge_max_mm=10.0)
    old_cost = mesh_io.support_cost(mesh, 45.0, 2.0, bridge_max_mm=10.0)
    assert [r["bridge"] for r in new_regions] == [r["bridge"] for r in old_regions]
    assert new_cost == old_cost


def _many_overhangs():
    parts = [trimesh.creation.box([60, 40, 10])]
    for i in range(4):
        for j in range(3):
            s = trimesh.creation.icosphere(subdivisions=2, radius=1.5)
            s.apply_translation([-20 + i * 13, -12 + j * 11, 7 + (i + j) % 3])
            parts.append(s)
    return trimesh.util.concatenate(parts)


def test_seeded_ctx_and_bulk_gate_match_per_region_bridge_flags():
    import mesh_io

    mesh = _many_overhangs()
    rot = trimesh.transformations.rotation_matrix(0.7, [1, 0.3, 0])
    mesh.apply_transform(rot)
    mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])
    seeded = {
        "centroids_z": np.asarray(mesh.triangles_center)[:, 2],
        "keys": mesh_io.edge_lookup(mesh)[0],
        "pairs": mesh_io.edge_lookup(mesh)[1],
    }
    plain = mesh_io.overhang_regions(mesh, 45.0, exclude_bed=True)
    fast = mesh_io.overhang_regions(mesh, 45.0, exclude_bed=True, ctx=seeded)
    assert plain and len(plain) == len(fast)
    for a, b in zip(plain, fast, strict=True):
        assert np.array_equal(a["faces"], b["faces"]) and a["bridge"] == b["bridge"]
    # bulk gate must agree with the in-function gate on every region
    angles = mesh_io._overhang_angles(mesh)
    sel = np.zeros(len(mesh.faces), bool)
    for r in plain:
        sel[r["faces"]] = True
        ref = mesh_io._is_bridge(mesh, r["faces"], sel, angles, mesh_io.BRIDGE_MAX_MM, {})
        assert ref == r["bridge"]
