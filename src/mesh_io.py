"""Pure trimesh STL loading with validation guards.

Kept separate from preview.py so consumers that only need mesh loading
(stl_to_3mf.py, run_cadquery_model.py's --strict watertight check) don't
pay the pyrender + PyOpenGL import cost. Only depends on trimesh + numpy.
"""

import os

import numpy as np
import trimesh

# Shared tessellation settings for deliverable STL/3MF export (stl.py, threemf_multi.py).
# Kept as one source of truth so the two exporters can't silently drift apart.
# preview.py intentionally uses its own coarser tolerance (speed over fidelity).
EXPORT_TESSELLATION_TOLERANCE_MM = 0.01
EXPORT_TESSELLATION_ANGULAR_TOLERANCE_DEG = 0.1


def load_mesh(path: str) -> trimesh.Trimesh:
    """Load an STL file via trimesh.

    Raises ValueError if the file cannot be parsed, contains no geometry,
    has zero faces, or has non-finite vertex coordinates. Callers handle
    the failure in-process instead of being killed by sys.exit, and silent
    garbage (zero-face or NaN meshes) is stopped before it reaches pyrender.
    """
    if not os.path.isfile(path):
        raise ValueError(f"STL not found: {path} (export it first, e.g. with --deliver)")
    try:
        tm = trimesh.load(path, force="mesh")
    except Exception as e:
        raise ValueError(f"Failed to load STL: {path} is not a valid STL file: {e}") from e
    if not isinstance(tm, trimesh.Trimesh) or len(tm.vertices) == 0:
        raise ValueError("STL file contains no vertices")
    if len(tm.faces) == 0:
        raise ValueError("STL file contains no triangles")
    if not np.isfinite(tm.vertices).all():
        raise ValueError("STL file has non-finite vertex coordinates (NaN or inf)")
    return tm


def nonmanifold_edge_count(mesh) -> int:
    """Count edges shared by other than exactly two faces, vectorized via numpy.

    Shared core used by both the STL topology check (`run_cadquery_model.py`) and
    the 3MF manifold check (`exporters/threemf_multi.count_nonmanifold_edges`) so
    non-manifold detection has one implementation instead of parallel copies.
    """
    edges = np.sort(mesh.edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int((counts != 2).sum())


def nonmanifold_edges(mesh, max_report=5):
    """Find edges shared by other than exactly two faces, vectorized via numpy.

    Returns up to `max_report` non-manifold edges (all of them if `max_report` is
    None) as `(vertex_index_pair, face_indices)` tuples. Empty for a manifold mesh.
    Unlike `nonmanifold_edge_count`, this resolves which faces touch each
    non-manifold edge, needed to report a gap distance and offending faces.
    """
    edges = np.sort(mesh.edges, axis=1)
    face_idx = np.repeat(np.arange(len(mesh.faces)), 3)
    unique_edges, inverse, counts = np.unique(
        edges, axis=0, return_inverse=True, return_counts=True
    )
    nm_edge_ids = np.nonzero(counts != 2)[0]
    if max_report is not None:
        nm_edge_ids = nm_edge_ids[:max_report]
    return [
        (tuple(int(v) for v in unique_edges[eid]), face_idx[inverse == eid].tolist())
        for eid in nm_edge_ids
    ]


# A steeply down-facing face whose centroid sits within this height of the mesh's
# lowest point is resting on the print bed: the bed supports it, so it is never an
# unsupported overhang. One first-layer height; shared with print_orientation.py.
FIRST_LAYER_BAND_MM = 0.3
# Default longest span (mm) an FDM printer bridges without support.
BRIDGE_MAX_MM = 10.0
# A region is only a bridge candidate when its mean overhang angle is this steep
# (near-horizontal ceiling).
BRIDGE_MIN_DEG = 80.0
# Fraction of a rectangle side that must be anchored for that side to count as supported.
BRIDGE_SIDE_COVERAGE = 0.5
# Bridge regions keep this fraction of their normal support cost.
BRIDGE_COST_FACTOR = 0.1


# Adjacent faces whose interior dihedral angle (180 deg minus the angle between their
# normals) is below this fold back on each other: a zero-thickness fin or knife edge,
# which slicers draw as a spike. Real corners and curves stay >= 90 deg; a ~20 deg
# wedge tip (a deliberate taper) stays well clear.
FOLD_MIN_INTERIOR_DEG = 10.0


def fold_metrics(mesh, min_interior_deg=FOLD_MIN_INTERIOR_DEG, max_report=5):
    """Fin / knife-edge folds: adjacent triangles whose interior dihedral is under
    `min_interior_deg`. Pose-independent (it compares neighbouring normals only).

    Fold pairs that touch (share a vertex) are one cluster, so a fin made of many
    triangle pairs along one seam reports once. Returns
    `{"count", "sharpest_deg", "clusters"}`, where `clusters` holds up to `max_report`
    dicts `{angle_deg, location_xyz_mm, min_face_area_mm2}`, sharpest first; `count`
    is every cluster found. Does not tell a convex wedge from a slit -- both are
    unprintable. Needs merged vertices (trimesh.load's default).
    """
    import scipy.sparse as sp
    from scipy.sparse.csgraph import connected_components

    interior = 180.0 - np.degrees(mesh.face_adjacency_angles)
    hit = np.nonzero(interior < min_interior_deg)[0]  # NaN (degenerate faces) never hits
    if len(hit) == 0:
        return {"count": 0, "sharpest_deg": None, "clusters": []}
    pairs = mesh.face_adjacency[hit]
    # Graph over vertices: both faces of a fold pair connect all their vertices.
    a = np.concatenate([mesh.faces[pairs[:, 0]], mesh.faces[pairs[:, 1]]])  # (2k, 3)
    rows, cols = np.repeat(a[:, 0], 2), a[:, 1:].ravel()
    n = len(mesh.vertices)
    graph = sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    _, label = connected_components(graph, directed=False)
    cluster_of = label[mesh.faces[pairs[:, 0], 0]]
    edges = mesh.face_adjacency_edges[hit]
    mid = mesh.vertices[edges].mean(axis=1)
    areas = np.minimum(mesh.area_faces[pairs[:, 0]], mesh.area_faces[pairs[:, 1]])
    found: list[tuple[float, dict]] = []
    for c in np.unique(cluster_of):
        sel = np.nonzero(cluster_of == c)[0]
        k = sel[np.argmin(interior[hit][sel])]
        found.append(
            (
                float(interior[hit][k]),
                {
                    "angle_deg": float(interior[hit][k]),
                    "location_xyz_mm": [float(x) for x in mid[k]],
                    "min_face_area_mm2": float(areas[sel].min()),
                },
            )
        )
    found.sort(key=lambda t: t[0])
    clusters = [d for _, d in found]
    return {
        "count": len(clusters),
        "sharpest_deg": clusters[0]["angle_deg"],
        "clusters": clusters[:max_report],
    }


def bed_contact_mask(mesh, centroids_z=None):
    """Faces resting on the bed: steeply down-facing, within one first-layer height of the floor.

    `centroids_z` is the per-face centroid z at this pose when the caller already has it.
    """
    min_z = float(mesh.vertices[:, 2].min())
    if centroids_z is None:
        centroids_z = mesh.triangles_center[:, 2]  # cached: shared by every call on this pose
    return bed_mask_from(mesh.face_normals[:, 2], centroids_z, min_z)


def bed_mask_from(normals_z, centroids_z, min_z):
    """Bed-contact mask from per-face normal z, centroid z and the pose's floor height.

    The single definition of bed contact: `bed_contact_mask` applies it to a posed mesh and
    the orientation search applies it to rotated normals without posing the mesh.
    """
    return (normals_z < -0.5) & (centroids_z <= min_z + FIRST_LAYER_BAND_MM)


# Lift-risk heuristic (after augura): a brim is advised when the bed contact is small or
# the part is tall relative to it (height / sqrt(contact area)).
BRIM_MIN_CONTACT_MM2 = 50.0
BRIM_MAX_HEIGHT_RATIO = 6.0
# Horizontal face planes closer than this (mm) are one plane.
PLANE_MERGE_MM = 1e-3


def brim_metrics(mesh):
    """Bed-contact area, height, height/sqrt(contact) and whether a brim is advised."""
    contact = float(mesh.area_faces[bed_contact_mask(mesh)].sum())
    height = float(np.ptp(mesh.vertices[:, 2]))
    ratio = height / contact**0.5 if contact > 0 else float("inf")
    return {
        "contact_area_mm2": round(contact, 3),
        "height_mm": round(height, 3),
        "height_ratio": round(ratio, 3),
        "recommended": contact < BRIM_MIN_CONTACT_MM2 or ratio > BRIM_MAX_HEIGHT_RATIO,
    }


def min_horizontal_gap(mesh):
    """Smallest Z gap (mm) between distinct horizontal face planes, with the two plane
    heights; None when the mesh has fewer than two such planes."""
    flat = np.abs(mesh.face_normals[:, 2]) > 1 - 1e-9
    zs = np.sort(mesh.triangles_center[flat, 2])
    gaps = np.diff(zs)
    real = np.flatnonzero(gaps > PLANE_MERGE_MM)
    if not len(real):
        return None
    i = int(real[gaps[real].argmin()])
    return float(gaps[i]), float(zs[i]), float(zs[i + 1])


def _overhang_angles(mesh):
    return np.degrees(np.arcsin(np.clip(-mesh.face_normals[:, 2], 0.0, 1.0)))


def edge_lookup(mesh):
    """Sorted edge keys and the face pair across each: pure connectivity, pose-invariant."""
    adj_edges = np.sort(mesh.face_adjacency_edges, axis=1).astype(np.int64)
    keys = adj_edges[:, 0] * len(mesh.vertices) + adj_edges[:, 1]
    order = np.argsort(keys, kind="stable")  # stable: duplicate edges resolve to the last pair
    return keys[order], np.asarray(mesh.face_adjacency)[order]


def _is_bridge(mesh, faces, in_region, angles, bridge_max_mm, ctx):
    """True when the region is a near-horizontal ceiling, at most `bridge_max_mm` across,
    supported on at least two sides of its oriented XY rectangle.

    A region boundary edge is anchored when the face across it descends from the edge
    (a wall the ceiling rests on); a wall rising from the edge is the region's own free
    lip. Anchored edges are binned to the 4 rectangle sides; a side counts as supported
    when anchored length covers BRIDGE_SIDE_COVERAGE of it.
    """
    # Mesh-wide arrays and the sorted edge-key -> face-pair map are built once per
    # overhang_regions call (shared via `ctx`): each trimesh property access re-verifies
    # its cache by hashing. A caller scoring many poses of one mesh may pre-seed "keys",
    # "pairs" (rotation-invariant) and "centroids_z" (per pose).
    if "verts" not in ctx:
        ctx["verts"] = np.asarray(mesh.vertices)
        ctx["tris"] = np.asarray(mesh.faces)
        ctx["area"] = np.asarray(mesh.area_faces)
    if "keys" not in ctx:
        ctx["keys"], ctx["pairs"] = edge_lookup(mesh)
    if "centroids_z" not in ctx:
        ctx["centroids_z"] = mesh.triangles.mean(axis=1)[:, 2]
    verts, centroids_z = ctx["verts"], ctx["centroids_z"]
    if np.average(angles[faces], weights=ctx["area"][faces]) < BRIDGE_MIN_DEG:
        return False
    tri = ctx["tris"][faces]
    pts = verts[np.unique(tri)][:, :2]
    if len(pts) < 3:
        return False
    to_rect, rect = trimesh.bounds.oriented_bounds_2D(pts)
    short = float(rect.min())
    if short > bridge_max_mm or short <= 0.0:
        return False

    # Region boundary edges: appear once among the region's own faces.
    edges = np.sort(tri[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    owner = np.repeat(faces, 3)
    _, inv, cnt = np.unique(
        edges[:, 0].astype(np.int64) * len(verts) + edges[:, 1],
        return_inverse=True,
        return_counts=True,
    )
    boundary = cnt[inv.reshape(-1)] == 1

    side_len = [rect[1], rect[1], rect[0], rect[0]]  # sides +x, -x, +y, -y
    e, f = edges[boundary], owner[boundary]
    if not len(ctx["keys"]):
        return False  # no adjacent faces: nothing anchors the region
    ek = e[:, 0].astype(np.int64) * len(verts) + e[:, 1]
    idx = np.searchsorted(ctx["keys"], ek, side="right") - 1
    found = (idx >= 0) & (ctx["keys"][np.maximum(idx, 0)] == ek)
    e, f, pair = e[found], f[found], ctx["pairs"][idx[found]]
    other = np.where(pair[:, 0] == f, pair[:, 1], pair[:, 0])
    a, b = verts[e[:, 0]], verts[e[:, 1]]
    mid = (a + b) / 2
    keep = ~in_region[other] & (centroids_z[other] < mid[:, 2] - 1e-6)  # else: free lip
    x, y = (np.column_stack([mid[:, :2], np.ones(len(mid))]) @ to_rect.T)[keep].T[:2]
    along_x = np.abs(x) / (rect[0] / 2) >= np.abs(y) / (rect[1] / 2)
    side = np.where(along_x, np.where(x > 0, 0, 1), np.where(y > 0, 2, 3))
    covered = np.bincount(side, weights=np.linalg.norm((a - b)[keep], axis=1), minlength=4)
    supported = sum(
        1 for c, n in zip(covered, side_len, strict=True) if c >= BRIDGE_SIDE_COVERAGE * n
    )
    return supported >= 2


def overhang_regions(
    mesh,
    overhang_deg,
    exclude_mask=None,
    bridge_max_mm=BRIDGE_MAX_MM,
    exclude_bed=False,
    ctx=None,
):
    """Connected regions of unsupported down-facing faces, each flagged as bridge or not.

    Returns a list of dicts {faces, area_mm2, bridge}. Faces in `exclude_mask`, and bed-contact
    faces when `exclude_bed`, are dropped first. Build direction
    is +Z, so this is pose-dependent. `ctx` optionally pre-seeds `_is_bridge`'s shared
    arrays ("keys", "pairs", "centroids_z"; see `_is_bridge`).
    """
    ctx = {} if ctx is None else ctx
    angles = _overhang_angles(mesh)
    sel = (mesh.face_normals[:, 2] < 0) & (angles > overhang_deg)
    if exclude_bed:
        sel = sel & ~bed_contact_mask(mesh, ctx.get("centroids_z"))
    if exclude_mask is not None:
        sel = sel & ~exclude_mask
    if not np.any(sel):
        return []
    adj = mesh.face_adjacency
    linked = adj[sel[adj[:, 0]] & sel[adj[:, 1]]]
    groups = trimesh.graph.connected_components(linked, nodes=np.nonzero(sel)[0], min_len=1)
    regions = []
    area = np.asarray(mesh.area_faces)
    ctx.update(area=area, tris=np.asarray(mesh.faces), verts=np.asarray(mesh.vertices))
    # Bulk angle gate: only regions averaging at least BRIDGE_MIN_DEG reach the geometry work.
    groups = [np.asarray(g) for g in groups]
    label = np.repeat(np.arange(len(groups)), [len(g) for g in groups])
    allf = np.concatenate(groups)
    w = np.bincount(label, weights=area[allf])
    gated = np.bincount(label, weights=angles[allf] * area[allf]) / w >= BRIDGE_MIN_DEG
    for faces, passes in zip(groups, gated, strict=True):
        bridge = bool(passes) and _is_bridge(mesh, faces, sel, angles, bridge_max_mm, ctx)
        regions.append({"faces": faces, "area_mm2": float(area[faces].sum()), "bridge": bridge})
    return regions


def overhang_metrics(mesh, overhang_deg, bridge_max_mm=BRIDGE_MAX_MM):
    """Overhang area and worst face for a mesh at its current pose.

    A face is an unsupported overhang when its normal points downward (nz < 0)
    and its angle from horizontal -- arcsin(-nz) for a unit normal -- exceeds
    `overhang_deg`. Faces resting on the print bed are NOT overhangs (see
    `bed_contact_mask`). Connected overhang faces form regions; a region that is a
    bridge (near-horizontal, at most `bridge_max_mm` across, supported on two or more
    sides -- see `_is_bridge`) prints without support, so it is reported in
    `bridge_area_mm2` / `bridge_count` and excluded from the overhang area and worst
    face. Returns a dict with the overhang area, the steepest remaining face's angle
    and centroid (None when nothing exceeds the threshold), and the bridge totals. The
    build direction is +Z, so this is pose-dependent: rotate the mesh to score a
    different print orientation.
    """
    regions = overhang_regions(mesh, overhang_deg, bridge_max_mm=bridge_max_mm, exclude_bed=True)
    bridges = [r for r in regions if r["bridge"]]
    real = [r for r in regions if not r["bridge"]]
    out = {
        "overhang_area_mm2": 0.0,
        "worst_angle_deg": None,
        "worst_location_xyz_mm": None,
        "bridge_area_mm2": round(sum(r["area_mm2"] for r in bridges), 3),
        "bridge_count": len(bridges),
    }
    if not real:
        return out
    faces = np.concatenate([r["faces"] for r in real])
    angles = _overhang_angles(mesh)
    worst_face = int(faces[int(angles[faces].argmax())])
    centroid = mesh.triangles[worst_face].mean(axis=0)
    out["overhang_area_mm2"] = round(float(mesh.area_faces[faces].sum()), 3)
    out["worst_angle_deg"] = round(float(angles[worst_face]), 3)
    out["worst_location_xyz_mm"] = [round(float(c), 3) for c in centroid]
    return out


def support_cost(
    mesh, overhang_deg, exponent, exclude_mask=None, bridge_max_mm=BRIDGE_MAX_MM, ctx=None
):
    """Severity-weighted unsupported-overhang cost at the mesh's current pose.

    Each unsupported down-facing face contributes its area scaled by how far it leans
    past `overhang_deg` (normalized to [0, 1] over the limit-to-horizontal range) raised
    to `exponent` (`OV_H`). The ramp is zero at the limit, so the cost is continuous
    there; with `exponent > 1` a near-horizontal face costs disproportionately more
    than one just past the limit. Faces of bridge regions keep only
    `BRIDGE_COST_FACTOR` of their cost. `exclude_mask` drops faces (e.g. those resting
    on the bed). Used for print-orientation ranking; `overhang_metrics` reports the
    true overhang area.
    """
    regions = overhang_regions(mesh, overhang_deg, exclude_mask, bridge_max_mm, ctx=ctx)
    if not regions:
        return 0.0
    angles = _overhang_angles(mesh)
    area = np.asarray(mesh.area_faces)
    total = 0.0
    for r in regions:
        f = r["faces"]
        lean = (angles[f] - overhang_deg) / (90.0 - overhang_deg)
        cost = float((area[f] * np.power(lean, exponent)).sum())
        total += cost * (BRIDGE_COST_FACTOR if r["bridge"] else 1.0)
    return round(total, 3)


def up_facing_incline_area(mesh, min_deg, max_deg):
    """Total area (mm^2) of UP-facing faces inclined within (min_deg, max_deg) of horizontal.

    A face is counted when its outward normal points up (nz > 0) and its inclination from
    horizontal -- arccos(nz) for a unit normal (0 = flat top, 90 = vertical wall) -- lies
    strictly inside the open band (min_deg, max_deg). This is the cosmetic stair-step band:
    a shallow up-facing slope prints as visible layer steps. Down-facing faces (nz < 0) are
    excluded -- a shallow one is an overhang, a separate concern owned by `overhang_metrics`
    -- so no separate bed-contact exclusion is needed (bed faces are down-facing). Build
    direction is +Z, so this is pose-dependent: pass a mesh already rotated into the print
    (build) frame.
    """
    nz = mesh.face_normals[:, 2]
    up_mask = nz > 0
    if not np.any(up_mask):
        return 0.0
    incline = np.degrees(np.arccos(np.clip(nz, 0.0, 1.0)))
    band_mask = up_mask & (incline > min_deg) & (incline < max_deg)
    return round(float(mesh.area_faces[band_mask].sum()), 3)


def lateral_area(mesh):
    """Total mesh area minus its up-facing and down-facing area (mm^2).

    For a prismatic (constant cross-section) part this is exactly the wall area swept
    by one layer's perimeter times the part's height, so `lateral_area(mesh) / H` is a
    cheap, no-sectioning estimate of mean layer perimeter -- see
    `toolpath_speed.py`. Up-facing and down-facing are partitioned by face-normal sign
    (nz > 0 / nz < 0), the same partition `bed_contact_mask` and `up_facing_incline_area`
    use, so the three sums never disagree about which face is which. Build direction is
    +Z, so this is pose-dependent: pass a mesh already rotated into the print (build)
    frame.
    """
    nz = mesh.face_normals[:, 2]
    # Tolerance: a rotated wall carries nz ~1e-16 noise and must still count as a wall.
    up = float(mesh.area_faces[nz > 1e-6].sum())
    down = float(mesh.area_faces[nz < -1e-6].sum())
    return round(float(mesh.area_faces.sum()) - up - down, 3)
