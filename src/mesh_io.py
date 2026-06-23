"""Pure trimesh STL loading with validation guards.

Kept separate from preview.py so consumers that only need mesh loading
(stl_to_3mf.py, run_cadquery_model.py's --strict watertight check) don't
pay the pyrender + PyOpenGL import cost. Only depends on trimesh + numpy.
"""

import numpy as np
import trimesh


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


def overhang_metrics(mesh, overhang_deg):
    """Overhang area and worst face for a mesh at its current pose.

    A face is an unsupported overhang when its normal points downward (nz < 0)
    and its angle from horizontal -- arcsin(-nz) for a unit normal -- exceeds
    `overhang_deg`. Returns a dict with the total such area, and the steepest
    face's angle and centroid (both None when nothing exceeds the threshold).
    The build direction is +Z, so this is pose-dependent: rotate the mesh to
    score a different print orientation. Shared by the quality gate and the
    print-orientation optimizer so both use one definition of "needs support".
    """
    normals = mesh.face_normals
    downward_mask = normals[:, 2] < 0
    if not np.any(downward_mask):
        return {
            "overhang_area_mm2": 0.0,
            "worst_angle_deg": None,
            "worst_location_xyz_mm": None,
        }

    angles = np.degrees(np.arcsin(np.clip(-normals[:, 2], 0.0, 1.0)))
    support_mask = downward_mask & (angles > overhang_deg)
    if not np.any(support_mask):
        return {
            "overhang_area_mm2": 0.0,
            "worst_angle_deg": None,
            "worst_location_xyz_mm": None,
        }

    overhang_area = float(mesh.area_faces[support_mask].sum())
    support_indices = np.nonzero(support_mask)[0]
    worst_face = int(support_indices[int(angles[support_indices].argmax())])
    centroid = mesh.triangles[worst_face].mean(axis=0)
    return {
        "overhang_area_mm2": round(overhang_area, 3),
        "worst_angle_deg": round(float(angles[worst_face]), 3),
        "worst_location_xyz_mm": [round(float(c), 3) for c in centroid],
    }


def support_cost(mesh, overhang_deg, exponent, exclude_mask=None):
    """Severity-weighted unsupported-overhang cost at the mesh's current pose.

    Unlike `overhang_metrics`' flat area sum, each unsupported downward face
    contributes its area scaled by how far it leans past `overhang_deg`
    (normalized to [0, 1] across the limit-to-horizontal range) raised to
    `exponent`. With `exponent > 1` a near-horizontal face costs
    disproportionately more than one just past the limit, matching the real
    cost of support material. Build direction is +Z, so this is pose-dependent.
    `exclude_mask` drops faces from the cost (e.g. the face resting on the bed,
    which is supported by the bed, not by support material). Used for
    print-orientation ranking only; `overhang_metrics` is left unchanged so the
    quality gate keeps reporting true overhang area.
    """
    nz = mesh.face_normals[:, 2]
    downward_mask = nz < 0
    if exclude_mask is not None:
        downward_mask = downward_mask & ~exclude_mask
    if not np.any(downward_mask):
        return 0.0

    angles = np.degrees(np.arcsin(np.clip(-nz, 0.0, 1.0)))
    support_mask = downward_mask & (angles > overhang_deg)
    if not np.any(support_mask):
        return 0.0

    lean = (angles[support_mask] - overhang_deg) / (90.0 - overhang_deg)
    weighted = mesh.area_faces[support_mask] * np.power(lean, exponent)
    return round(float(weighted.sum()), 3)
