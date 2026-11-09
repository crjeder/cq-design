# mypy: ignore-errors
# type: ignore  # trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Vectorized mesh helpers must match the original per-element loop implementations."""

import numpy as np
import trimesh

from measure_stl import _cylinders, _flat_faces, _union_find
from print_orientation import AREA_CUMULATION_TOP_N, _area_cumulation_normals, _unit


def _union_find_ref(nodes, edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    return list(groups.values())


def _area_cumulation_ref(mesh, top_n=AREA_CUMULATION_TOP_N):
    keys = np.round(mesh.face_normals, 2)
    buckets = {}
    for key, normal, area in zip(map(tuple, keys), mesh.face_normals, mesh.area_faces, strict=True):
        acc = buckets.get(key)
        if acc is None:
            buckets[key] = [float(area), normal * area]
        else:
            acc[0] += float(area)
            acc[1] = acc[1] + normal * area
    ranked = sorted(buckets.values(), key=lambda b: b[0], reverse=True)
    return [_unit(b[1]) for b in ranked[:top_n]]


def _flat_faces_ref(mesh, min_area_mm2):
    z_comp = np.abs(mesh.face_normals[:, 2])
    is_flat = z_comp > 0.9
    if not np.any(is_flat):
        return []
    idx = np.where(is_flat)[0]
    z_pos = mesh.triangles_center[idx, 2]
    areas = mesh.area_faces[idx]
    nz = mesh.face_normals[idx, 2]
    order = np.argsort(z_pos)
    z_s, a_s, nz_s, orig_s = z_pos[order], areas[order], nz[order], idx[order]
    used = np.zeros(len(idx), dtype=bool)
    results = []
    for i in range(len(idx)):
        if used[i]:
            continue
        group = (~used) & (np.abs(z_s - z_s[i]) < 0.3)
        total_area = float(a_s[group].sum())
        if total_area < min_area_mm2:
            used |= group
            continue
        mean_z = float(np.average(z_s[group], weights=a_s[group]))
        direction = "up" if float(nz_s[group].mean()) > 0 else "down"
        verts_xy = mesh.vertices[mesh.faces[orig_s[group]].flatten(), :2]
        center_xy = verts_xy.mean(axis=0)
        bounding_r = float(np.linalg.norm(verts_xy - center_xy, axis=1).max())
        results.append(
            {
                "z_mm": round(mean_z, 2),
                "area_mm2": round(total_area, 2),
                "center_xy_mm": [round(float(center_xy[0]), 2), round(float(center_xy[1]), 2)],
                "bounding_circle_r_mm": round(bounding_r, 2),
                "normal_dir": direction,
            }
        )
        used |= group
    return sorted(results, key=lambda r: r["z_mm"])


def _meshes():
    stepped = trimesh.util.concatenate(
        [
            trimesh.creation.box([20, 20, 2]),
            trimesh.creation.box([10, 10, 2]).apply_translation([0, 0, 2]),
            trimesh.creation.cylinder(radius=3, height=5, sections=24).apply_translation([8, 0, 1]),
        ]
    )
    rot = trimesh.transformations.rotation_matrix(0.3, [1, 1, 0])
    return [
        stepped,
        trimesh.creation.icosphere(subdivisions=3),
        trimesh.creation.box([5, 6, 7]).apply_transform(rot),
    ]


def test_union_find_matches_reference():
    rng = np.random.default_rng(0)
    for n, m in [(1, 0), (50, 30), (200, 150), (200, 400)]:
        nodes = sorted(rng.choice(1000, n, replace=False).tolist())
        edges = rng.choice(nodes, (m, 2)) if m else np.zeros((0, 2), dtype=int)
        assert _union_find(nodes, edges) == _union_find_ref(nodes, edges)
    assert _union_find([], np.zeros((0, 2), dtype=int)) == []


def test_area_cumulation_matches_reference():
    for mesh in _meshes():
        got, want = _area_cumulation_normals(mesh), _area_cumulation_ref(mesh)
        assert len(got) == len(want)
        assert all(np.array_equal(g, w) for g, w in zip(got, want, strict=True))


def test_flat_faces_matches_reference():
    for mesh in _meshes():
        assert _flat_faces(mesh, 1.0) == _flat_faces_ref(mesh, 1.0)


def test_columns_are_classified_by_side_count():
    cases = [
        (trimesh.creation.box([40, 20, 10]), "cuboid", 4),
        (trimesh.creation.cylinder(5, 10, sections=3), "triangle", 3),
        (trimesh.creation.cylinder(5, 10, sections=6), "polygon", 6),
        (trimesh.creation.cylinder(5, 10, sections=64), "cylinder", 64),
    ]
    for mesh, shape, sides in cases:
        (col,) = _cylinders(mesh, 0.5, 1.0)
        assert (col["shape"], col["sides"]) == (shape, sides)
