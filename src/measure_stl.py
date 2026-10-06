#!/usr/bin/env python3
"""Geometric feature extractor for STL files.

Detects bounding box, horizontal layers (flanges, steps, rims), and vertical
cylindrical features (bosses, holes) from face normals and connectivity.

Only depends on trimesh and numpy (already in pyproject.toml).

Outputs structured JSON to stdout; exits 1 and writes JSON error to stderr on
failure so callers can always parse the output.

Usage:
    python src/measure_stl.py model.stl
    python src/measure_stl.py model.stl --min-radius 1.0 --min-area 10.0
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load(path: str) -> trimesh.Trimesh:
    """Load and validate an STL file."""
    if not os.path.isfile(path):
        raise ValueError(f"STL not found: {path} (export it first, e.g. with --deliver)")
    try:
        mesh = trimesh.load(path, force="mesh")
    except Exception as e:
        raise ValueError(f"Cannot load STL: {path} is not a valid STL file: {e}") from e
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError("File contains no usable mesh geometry")
    return mesh


# ---------------------------------------------------------------------------
# Flat horizontal layers (flanges, rims, steps)
# ---------------------------------------------------------------------------


def _flat_faces(mesh: trimesh.Trimesh, min_area_mm2: float) -> list[dict]:
    """Return groups of horizontal faces sorted by ascending Z height.

    Groups faces whose normals are within ~26 deg of vertical (|nz| > 0.9)
    and merges those within 0.3 mm of each other.
    """
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
        # z_s is sorted: only a window around z_s[i] can be within 0.3 mm
        lo = np.searchsorted(z_s, z_s[i] - 0.3 - 1e-9, "left")
        hi = np.searchsorted(z_s, z_s[i] + 0.3 + 1e-9, "right")
        group = np.zeros(len(idx), dtype=bool)
        group[lo:hi] = (~used[lo:hi]) & (np.abs(z_s[lo:hi] - z_s[i]) < 0.3)
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
                "center_xy_mm": [
                    round(float(center_xy[0]), 2),
                    round(float(center_xy[1]), 2),
                ],
                "bounding_circle_r_mm": round(bounding_r, 2),
                "normal_dir": direction,
            }
        )
        used |= group

    return sorted(results, key=lambda r: r["z_mm"])


# ---------------------------------------------------------------------------
# Cylindrical features (bosses, holes)
# ---------------------------------------------------------------------------


def _union_find(nodes: list[int], edges: np.ndarray) -> list[list[int]]:
    """Return connected components as lists of node IDs.

    Components are ordered by their first node in `nodes`; members keep `nodes` order.
    """
    if not nodes:
        return []
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    arr = np.asarray(nodes, dtype=np.int64)
    lookup = np.full(int(arr.max()) + 1, -1, dtype=np.int64)
    lookup[arr] = np.arange(len(arr))
    edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    ij = lookup[edges]  # callers only pass edges whose endpoints are in `nodes`
    n = len(arr)
    graph = coo_matrix((np.ones(len(ij), dtype=np.int8), (ij[:, 0], ij[:, 1])), shape=(n, n))
    _, label = connected_components(graph, directed=False)

    order = np.argsort(label, kind="stable")  # stable: members stay in `nodes` order
    starts = np.flatnonzero(np.diff(label[order], prepend=-1))
    groups = np.split(arr[order], starts[1:])
    first = order[starts]  # position in `nodes` of each group's first member
    return [groups[g].tolist() for g in np.argsort(first)]


def _cylinders(mesh: trimesh.Trimesh, min_radius_mm: float, min_area_mm2: float) -> list[dict]:
    """Detect vertical cylindrical features grouped by face adjacency.

    Classifies each group as boss (outward-pointing normals) or hole
    (inward-pointing normals) by comparing face normals against the
    radial direction from the fitted axis center.
    """
    # Side faces: normal mostly horizontal and well-defined
    z_abs = np.abs(mesh.face_normals[:, 2])
    nxy_len = np.linalg.norm(mesh.face_normals[:, :2], axis=1)
    is_side = (z_abs < 0.3) & (nxy_len > 0.8)

    if not np.any(is_side):
        return []

    # Filter face adjacency to side-face pairs only
    side_flags = np.zeros(len(mesh.faces), dtype=bool)
    side_flags[is_side] = True
    adj = mesh.face_adjacency  # (E, 2)
    adj_mask = side_flags[adj[:, 0]] & side_flags[adj[:, 1]]
    sub_adj = adj[adj_mask]

    side_idx = np.where(is_side)[0].tolist()
    components = _union_find(side_idx, sub_adj)

    results: list[dict[str, Any]] = []
    for comp in components:
        comp_arr = np.array(comp)
        total_area = float(mesh.area_faces[comp_arr].sum())
        if total_area < min_area_mm2:
            continue

        # Fit center and radius from vertices
        verts = mesh.vertices[mesh.faces[comp_arr].flatten()]
        xy = verts[:, :2]
        center = xy.mean(axis=0)
        dists = np.linalg.norm(xy - center, axis=1)
        radius = float(dists.mean())

        if radius < min_radius_mm:
            continue

        # Boss vs hole: dot(face_normal_xy, outward_radial) > 0 means boss
        cent_xy = mesh.triangles_center[comp_arr, :2]
        nxy = mesh.face_normals[comp_arr, :2]
        nxy_hat = nxy / np.maximum(np.linalg.norm(nxy, axis=1, keepdims=True), 1e-9)
        to_surface = cent_xy - center  # outward direction from axis
        dot = float(np.sum(nxy_hat * to_surface, axis=1).mean())
        feat_type = "boss" if dot > 0 else "hole"

        z_vals = verts[:, 2]
        results.append(
            {
                "type": feat_type,
                "axis": "z",
                "center_xy_mm": [
                    round(float(center[0]), 2),
                    round(float(center[1]), 2),
                ],
                "radius_mm": round(radius, 2),
                "diameter_mm": round(radius * 2, 2),
                "z_range_mm": [
                    round(float(z_vals.min()), 2),
                    round(float(z_vals.max()), 2),
                ],
                "height_mm": round(float(z_vals.max() - z_vals.min()), 2),
            }
        )

    results.sort(key=lambda r: -r["radius_mm"])
    return results


# ---------------------------------------------------------------------------
# Thin regions (local wall-thickness field with XY/Z direction classification)
# ---------------------------------------------------------------------------


def _ray_thickness(
    v0: np.ndarray,
    e1: np.ndarray,
    e2: np.ndarray,
    origin: np.ndarray,
    direction: np.ndarray,
    tmin: float,
) -> float:
    """Nearest forward ray-triangle hit distance (Moeller-Trumbore, vectorized).

    Returns the smallest t > tmin where the ray from ``origin`` along
    ``direction`` crosses a triangle, or inf if it never does.
    """
    pvec = np.cross(direction, e2)
    det = np.einsum("ij,ij->i", e1, pvec)
    ok = np.abs(det) > 1e-9
    inv = np.zeros_like(det)
    inv[ok] = 1.0 / det[ok]

    tvec = origin - v0
    u = np.einsum("ij,ij->i", tvec, pvec) * inv
    qvec = np.cross(tvec, e1)
    v = np.einsum("j,ij->i", direction, qvec) * inv
    t = np.einsum("ij,ij->i", e2, qvec) * inv

    hit = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > tmin)
    return float(t[hit].min()) if np.any(hit) else float("inf")


def _sampled_thickness(
    mesh: trimesh.Trimesh, idx: np.ndarray, tmin: float, prefilter: bool = True
) -> np.ndarray:
    """Inward-ray wall thickness for the faces in ``idx`` (inf elsewhere).

    On a watertight mesh the first crossing of an inward ray is the exit wall, whose
    outward normal points along the ray (n_tri . d > 0) and which lies beyond ``tmin``.
    The default path runs one batched ``mesh.ray`` query for all rays and reduces the
    qualifying hits per ray. ``prefilter=False`` tests every triangle per ray in a
    Python loop (reference path).
    """
    origins = mesh.triangles_center[idx]
    dirs = -mesh.face_normals[idx]
    thickness = np.full(len(mesh.faces), np.inf)

    if prefilter:
        loc, ray_i, tri_i = mesh.ray.intersects_location(origins, dirs, multiple_hits=True)
        t = np.linalg.norm(loc - origins[ray_i], axis=1)
        keep = (np.einsum("ij,ij->i", mesh.face_normals[tri_i], dirs[ray_i]) > 1e-9) & (t > tmin)
        best = np.full(len(idx), np.inf)
        np.minimum.at(best, ray_i[keep], t[keep])
        thickness[idx] = best
        return thickness

    tris = mesh.triangles
    v0 = tris[:, 0]
    e1 = tris[:, 1] - v0
    e2 = tris[:, 2] - v0
    for k in range(len(idx)):
        thickness[idx[k]] = _ray_thickness(v0, e1, e2, origins[k], dirs[k], tmin)
    return thickness


def _nearest_feature(
    point: np.ndarray,
    flat_faces: list[dict],
    cylinders: list[dict],
    snap_radius_mm: float,
) -> dict | None:
    """Snap a thin-region point to the nearest detected feature within a radius.

    Returns {"feature": label, "distance_mm": d} or None if nothing is near.
    """
    best_label: str | None = None
    best_dist = snap_radius_mm

    for ff in flat_faces:
        cx, cy = ff["center_xy_mm"]
        fp = np.array([cx, cy, ff["z_mm"]])
        d = float(np.linalg.norm(point - fp))
        if d < best_dist:
            best_dist, best_label = d, f"flat_face@z{ff['z_mm']}"

    for cyl in cylinders:
        cx, cy = cyl["center_xy_mm"]
        mid_z = sum(cyl["z_range_mm"]) / 2.0
        fp = np.array([cx, cy, mid_z])
        d = float(np.linalg.norm(point - fp))
        if d < best_dist:
            best_dist = d
            best_label = f"{cyl['type']}@({cx},{cy})"

    if best_label is None:
        return None
    return {"feature": best_label, "distance_mm": round(best_dist, 2)}


def _thin_regions(
    mesh: trimesh.Trimesh,
    flat_faces: list[dict],
    cylinders: list[dict],
    thin_max_mm: float,
    line_width_mm: float,
    max_samples: int,
    snap_radius_mm: float,
) -> list[dict]:
    """Detect thin material regions via inward ray-cast wall thickness.

    For sampled faces, casts a ray inward along the inverse normal and measures
    the distance to the opposite wall. Faces thinner than ``thin_max_mm`` are
    grouped by face adjacency; each group is classified as thin-in-XY (the thin
    direction lies in the build plane -> a printability concern) or thin-in-Z (a
    flat, well-bonded slab -> benign) from the dominant normal axis.
    """
    n_faces = len(mesh.faces)
    if n_faces == 0:
        return []

    idx = np.arange(n_faces)
    if n_faces > max_samples:
        idx = idx[:: int(np.ceil(n_faces / max_samples))]

    # Wall thickness = distance to the opposite wall along the inward normal.
    tmin = 1e-3

    sampled = np.zeros(n_faces, dtype=bool)
    sampled[idx] = True

    thickness = _sampled_thickness(mesh, idx, tmin)

    is_thin = thickness < thin_max_mm
    if int(is_thin.sum()) < 2:
        return []

    # Group thin (seed) faces into regions, robust to triangle density. The ray-cast
    # only measures the subsampled faces, so on a mesh above `max_samples` the thin
    # seeds of one wall are stride-spaced and rarely share an edge. Reconnect them by
    # flooding through the full adjacency graph, treating unmeasured (unsampled) faces
    # as transparent and only confirmed-thick (sampled, not-thin) faces as barriers.
    # Below the cap every face is sampled, so this reduces to thin-thin adjacency.
    barrier = sampled & ~is_thin
    adj = mesh.face_adjacency
    open_adj = adj[~barrier[adj[:, 0]] & ~barrier[adj[:, 1]]]
    components = _union_find(np.where(~barrier)[0].tolist(), open_adj)

    results: list[dict[str, Any]] = []
    for comp in components:
        seeds = [f for f in comp if is_thin[f]]
        if len(seeds) < 2:
            continue
        comp_arr = np.array(seeds)
        c_norm = mesh.face_normals[comp_arr]
        # Thinness axis is the dominant normal direction; sum of outer products
        # makes +n and -n (the two faces of a wall) reinforce instead of cancel.
        m = c_norm.T @ c_norm
        axis = np.linalg.eigh(m)[1][:, -1]
        axis = axis / max(np.linalg.norm(axis), 1e-9)
        orientation = "xy" if abs(float(axis[2])) < 0.707 else "z"

        centroid = mesh.triangles_center[comp_arr].mean(axis=0)
        t_min = float(thickness[comp_arr].min())
        t_mean = float(thickness[comp_arr].mean())

        results.append(
            {
                "thickness_mm": round(t_min, 2),
                "thickness_mean_mm": round(t_mean, 2),
                "equiv_diameter_mm": round(t_min, 2),
                "orientation": orientation,
                "thin_direction": [round(float(v), 3) for v in axis],
                "location_xyz_mm": [round(float(v), 2) for v in centroid],
                "brittle": bool(t_min < 4 * line_width_mm),
                "nearest_feature": _nearest_feature(
                    centroid, flat_faces, cylinders, snap_radius_mm
                ),
            }
        )

    results.sort(key=lambda r: r["thickness_mm"])
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def measure(
    path: str,
    min_radius_mm: float = 1.0,
    min_area_mm2: float = 5.0,
    thin_max_mm: float = 2.0,
    line_width_mm: float = 0.42,
    max_samples: int = 3000,
) -> dict:
    """Extract geometric features from an STL file.

    Returns a dict with keys: source_stl, is_watertight, bounding_box_mm,
    volume_cm3, flat_faces, cylinders, thin_regions.
    """
    mesh = _load(path)
    ex = mesh.extents
    vol = round(float(mesh.volume) / 1000.0, 3) if mesh.is_watertight else None

    flat_faces = _flat_faces(mesh, min_area_mm2)
    cylinders = _cylinders(mesh, min_radius_mm, min_area_mm2)

    return {
        "source_stl": Path(path).name,
        "is_watertight": bool(mesh.is_watertight),
        "bounding_box_mm": {
            "x": round(float(ex[0]), 2),
            "y": round(float(ex[1]), 2),
            "z": round(float(ex[2]), 2),
        },
        "volume_cm3": vol,
        "flat_faces": flat_faces,
        "cylinders": cylinders,
        "thin_regions": _thin_regions(
            mesh,
            flat_faces,
            cylinders,
            thin_max_mm=thin_max_mm,
            line_width_mm=line_width_mm,
            max_samples=max_samples,
            snap_radius_mm=15.0,
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract geometric features from an STL file (bounding box, layers, cylinders)"
    )
    parser.add_argument("stl", help="Path to STL file")
    parser.add_argument(
        "--min-radius",
        type=float,
        default=1.0,
        metavar="MM",
        help="Minimum cylinder radius to report (default: 1.0 mm)",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=5.0,
        metavar="MM2",
        help="Minimum flat-face group area to report (default: 5.0 mm2)",
    )
    parser.add_argument(
        "--thin-max",
        type=float,
        default=2.0,
        metavar="MM",
        help="Report material regions thinner than this (default: 2.0 mm)",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=0.42,
        metavar="MM",
        help="Extrusion line width for the brittle threshold (default: 0.42 mm)",
    )
    args = parser.parse_args()

    try:
        result = measure(
            args.stl,
            min_radius_mm=args.min_radius,
            min_area_mm2=args.min_area,
            thin_max_mm=args.thin_max,
            line_width_mm=args.line_width,
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
