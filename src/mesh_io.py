"""Pure trimesh STL loading with validation guards.

Kept separate from preview.py so consumers that only need mesh loading
(stl_to_3mf.py, run_cadquery_model.py's --strict watertight check) don't
pay the pyrender + PyOpenGL import cost. Only depends on trimesh + numpy.
"""

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
    try:
        tm = trimesh.load(path, force="mesh")
    except Exception as e:
        raise ValueError(f"Failed to load STL: {e}") from e
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


def bed_contact_mask(mesh):
    """Faces resting on the bed: steeply down-facing, within one first-layer height of the floor."""
    min_z = float(mesh.vertices[:, 2].min())
    centroids_z = mesh.triangles.mean(axis=1)[:, 2]
    return (mesh.face_normals[:, 2] < -0.5) & (centroids_z <= min_z + FIRST_LAYER_BAND_MM)


def _overhang_angles(mesh):
    return np.degrees(np.arcsin(np.clip(-mesh.face_normals[:, 2], 0.0, 1.0)))


def _is_bridge(mesh, faces, in_region, angles, bridge_max_mm):
    """True when the region is a near-horizontal ceiling, at most `bridge_max_mm` across,
    supported on at least two sides of its oriented XY rectangle.

    A region boundary edge is anchored when the face across it descends from the edge
    (a wall the ceiling rests on); a wall rising from the edge is the region's own free
    lip. Anchored edges are binned to the 4 rectangle sides; a side counts as supported
    when anchored length covers BRIDGE_SIDE_COVERAGE of it.
    """
    area = mesh.area_faces[faces]
    if np.average(angles[faces], weights=area) < BRIDGE_MIN_DEG:
        return False
    tri = mesh.faces[faces]
    pts = mesh.vertices[np.unique(tri)][:, :2]
    if len(pts) < 3:
        return False
    to_rect, rect = trimesh.bounds.oriented_bounds_2D(pts)
    short = float(rect.min())
    if short > bridge_max_mm or short <= 0.0:
        return False

    # Region boundary edges: appear once among the region's own faces.
    edges = np.sort(tri[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    owner = np.repeat(faces, 3)
    _, inv, cnt = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    boundary = cnt[inv.reshape(-1)] == 1

    # Face across each boundary edge, via the mesh's edge -> face map.
    adj_edges = np.sort(mesh.face_adjacency_edges, axis=1)
    lookup = {
        tuple(e): (int(f[0]), int(f[1]))
        for e, f in zip(adj_edges, mesh.face_adjacency, strict=True)
    }
    centroids_z = mesh.triangles.mean(axis=1)[:, 2]
    side_len = [rect[1], rect[1], rect[0], rect[0]]  # sides +x, -x, +y, -y
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
        mid = mesh.vertices[e].mean(axis=0)
        if centroids_z[other] >= mid[2] - 1e-6:
            continue  # wall rises from the edge: the region's own free lip
        x, y, _ = to_rect @ np.array([mid[0], mid[1], 1.0])
        if abs(x) / (rect[0] / 2) >= abs(y) / (rect[1] / 2):
            side = 0 if x > 0 else 1
        else:
            side = 2 if y > 0 else 3
        covered[side] += np.linalg.norm(mesh.vertices[e[0]] - mesh.vertices[e[1]])
    supported = sum(
        1 for c, n in zip(covered, side_len, strict=True) if c >= BRIDGE_SIDE_COVERAGE * n
    )
    return supported >= 2


def overhang_regions(
    mesh, overhang_deg, exclude_mask=None, bridge_max_mm=BRIDGE_MAX_MM, exclude_bed=False
):
    """Connected regions of unsupported down-facing faces, each flagged as bridge or not.

    Returns a list of dicts {faces, area_mm2, bridge}. Faces in `exclude_mask`, and bed-contact
    faces when `exclude_bed`, are dropped first. Build direction
    is +Z, so this is pose-dependent.
    """
    angles = _overhang_angles(mesh)
    sel = (mesh.face_normals[:, 2] < 0) & (angles > overhang_deg)
    if exclude_bed:
        sel = sel & ~bed_contact_mask(mesh)
    if exclude_mask is not None:
        sel = sel & ~exclude_mask
    if not np.any(sel):
        return []
    adj = mesh.face_adjacency
    linked = adj[sel[adj[:, 0]] & sel[adj[:, 1]]]
    groups = trimesh.graph.connected_components(linked, nodes=np.nonzero(sel)[0], min_len=1)
    regions = []
    for faces in groups:
        faces = np.asarray(faces)
        bridge = _is_bridge(mesh, faces, sel, angles, bridge_max_mm)
        regions.append(
            {"faces": faces, "area_mm2": float(mesh.area_faces[faces].sum()), "bridge": bridge}
        )
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


def support_cost(mesh, overhang_deg, exponent, exclude_mask=None, bridge_max_mm=BRIDGE_MAX_MM):
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
    regions = overhang_regions(mesh, overhang_deg, exclude_mask, bridge_max_mm)
    if not regions:
        return 0.0
    angles = _overhang_angles(mesh)
    total = 0.0
    for r in regions:
        f = r["faces"]
        lean = (angles[f] - overhang_deg) / (90.0 - overhang_deg)
        cost = float((mesh.area_faces[f] * np.power(lean, exponent)).sum())
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
    up = float(mesh.area_faces[nz > 0].sum())
    down = float(mesh.area_faces[nz < 0].sum())
    return round(float(mesh.area_faces.sum()) - up - down, 3)
