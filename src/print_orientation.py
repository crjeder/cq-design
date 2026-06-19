#!/usr/bin/env python3
"""Print-orientation optimizer: choose how a union sits on the bed.

For a union mesh in its authored frame, enumerate stable bed-down orientations
(convex-hull resting facets + the six axis-aligned faces), score each on:

  - strength (primary): how well the part's load direction stays in the layer
    plane (perpendicular to build +Z). FDM is weakest across layers, so a load
    that runs along Z is the worst case. Score = 1 - |load_after_rotation . Z|.
  - support (secondary): downward-facing area above the overhang limit at that
    pose (a slicer-free proxy for support volume; less is better), with bed
    contact area as a tiebreaker (more contact prints more reliably).

Selection is lexicographic: best strength first, ties within a tolerance band
broken by least support. The load direction is the part's declared `load.dir`
when present and a geometry-inferred principal axis otherwise.

The recommended orientation is emitted as a rotation in the placement.py
convention (ordered X/Y/Z steps), so the model export can apply it the same way
it applies a `placement`. It is distinct from the union's assembled-frame
`placement` and never overwrites it.

Usage:
    python3 print_orientation.py union.stl --overhang-max-deg 45
    python3 print_orientation.py union.stl --overhang-max-deg 45 --load 1,0,0
"""

import argparse
import json
import sys

import numpy as np
import trimesh
from trimesh.transformations import euler_from_matrix

from mesh_io import load_mesh, overhang_metrics

# A candidate strength within this band of the best is treated as tied, so the
# decision falls to support. Prevents jitter between near-identical poses.
STRENGTH_BAND = 0.02
# Two bed-down normals within this angle are the same resting face.
NORMAL_MERGE_DEG = 5.0
# Face counts as bed contact when nearly flat-down and within this of the floor.
CONTACT_Z_EPS_MM = 0.05
_DOWN = np.array([0.0, 0.0, -1.0])
_AXIS_NORMALS = [
    np.array([1.0, 0.0, 0.0]),
    np.array([-1.0, 0.0, 0.0]),
    np.array([0.0, 1.0, 0.0]),
    np.array([0.0, -1.0, 0.0]),
    np.array([0.0, 0.0, 1.0]),
    np.array([0.0, 0.0, -1.0]),
]


def _unit(vec: np.ndarray) -> np.ndarray:
    """Return the unit vector; unchanged direction, length 1."""
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def enumerate_candidate_normals(
    mesh: trimesh.Trimesh, merge_deg: float = NORMAL_MERGE_DEG
) -> list[np.ndarray]:
    """Bed-down normals to test: convex-hull facets + 6 axis-aligned faces.

    A part rests stably on a convex-hull face, so each unique hull-facet outward
    normal is a candidate "down" direction; the axis-aligned six are always
    included as a baseline. Normals within `merge_deg` are deduplicated so the
    set stays bounded on organic meshes.
    """
    normals: list[np.ndarray] = [n.copy() for n in _AXIS_NORMALS]
    try:
        hull_normals = mesh.convex_hull.face_normals
    except Exception:
        hull_normals = np.empty((0, 3))
    for n in hull_normals:
        normals.append(_unit(np.asarray(n, dtype=float)))

    cos_tol = np.cos(np.radians(merge_deg))
    kept: list[np.ndarray] = []
    for n in normals:
        if not any(float(np.dot(n, k)) >= cos_tol for k in kept):
            kept.append(n)
    return kept


def _rotation_to_bed(down_normal: np.ndarray) -> np.ndarray:
    """4x4 rotation mapping `down_normal` to -Z (lays that face on the bed)."""
    return trimesh.geometry.align_vectors(_unit(down_normal), _DOWN)


def _strength_score(rotation: np.ndarray, load_dir: np.ndarray) -> float:
    """1.0 when the rotated load lies in the layer plane, 0.0 when along build Z."""
    load_after = rotation[:3, :3] @ _unit(load_dir)
    return round(1.0 - abs(float(load_after[2])), 6)


def _support_metrics(
    mesh: trimesh.Trimesh, rotation: np.ndarray, overhang_deg: float
) -> tuple[float, float]:
    """Return (support_area, bed_contact_area) for the mesh at the given pose.

    `overhang_metrics` counts every downward face above the angle limit, which
    includes the flat face resting on the bed (normal straight down). That face
    is supported by the bed, not by support material, so the bed-contact area is
    subtracted to give the true unsupported overhang area (lower is better).
    """
    posed = mesh.copy()
    posed.apply_transform(rotation)
    overhang_area = overhang_metrics(posed, overhang_deg)["overhang_area_mm2"]

    min_z = float(posed.vertices[:, 2].min())
    centroids_z = posed.triangles.mean(axis=1)[:, 2]
    contact_mask = (posed.face_normals[:, 2] < -0.5) & (
        centroids_z <= min_z + CONTACT_Z_EPS_MM
    )
    bed_contact = float(posed.area_faces[contact_mask].sum())
    support_area = max(0.0, overhang_area - bed_contact)
    return round(support_area, 3), round(bed_contact, 3)


def _infer_load_dir(mesh: trimesh.Trimesh) -> np.ndarray:
    """Conservative load axis: the longest bounding-box axis (most bend-prone)."""
    extents = mesh.bounding_box.extents
    axis = int(np.argmax(extents))
    vec = np.zeros(3)
    vec[axis] = 1.0
    return vec


def _rotation_to_placement(rotation: np.ndarray) -> list[dict]:
    """Decompose a rotation into ordered X/Y/Z steps (placement.py convention).

    placement.to_matrix composes steps as Rz @ Ry @ Rx, which is exactly the
    'sxyz' (static X-Y-Z) Euler convention, so the decomposed angles reconstruct
    the same orientation when applied in [X, Y, Z] order.
    """
    ax, ay, az = euler_from_matrix(rotation, axes="sxyz")
    return [
        {"axis": "X", "angle_deg": round(float(np.degrees(ax)), 4)},
        {"axis": "Y", "angle_deg": round(float(np.degrees(ay)), 4)},
        {"axis": "Z", "angle_deg": round(float(np.degrees(az)), 4)},
    ]


def _select(candidates: list[dict], strength_band: float) -> dict:
    """Pick a candidate strength-first, support-second (lexicographic).

    The best-strength candidate wins outright; any candidate within
    `strength_band` of it is a tie decided by least support, then most bed
    contact, then lowest index (deterministic).
    """
    best_strength = max(c["strength"] for c in candidates)
    contenders = [
        c for c in candidates if best_strength - c["strength"] <= strength_band
    ]
    return min(contenders, key=lambda c: (c["support"], -c["bed_contact"], c["idx"]))


def optimize_orientation(
    mesh: trimesh.Trimesh,
    overhang_deg: float,
    load_dir: list[float] | None = None,
    strength_band: float = STRENGTH_BAND,
) -> dict:
    """Choose the print orientation for a union mesh (strength first, support second).

    `load_dir` is the principal load in the mesh's own frame; inferred from
    geometry when None. Returns the recommended rotation (placement convention),
    the score breakdown, the load used, and a human-readable rationale.
    """
    inferred = load_dir is None
    load_vec = _infer_load_dir(mesh) if inferred else np.asarray(load_dir, dtype=float)

    candidates = []
    for idx, normal in enumerate(enumerate_candidate_normals(mesh)):
        rotation = _rotation_to_bed(normal)
        strength = _strength_score(rotation, load_vec)
        overhang_area, bed_contact = _support_metrics(mesh, rotation, overhang_deg)
        candidates.append(
            {
                "idx": idx,
                "rotation": rotation,
                "strength": strength,
                "support": overhang_area,
                "bed_contact": bed_contact,
            }
        )

    chosen = _select(candidates, strength_band)

    load_used = [round(float(v), 6) for v in _unit(load_vec)]
    rationale = (
        f"Strength {chosen['strength']:.3f} (load {'inferred from geometry' if inferred else 'declared'} "
        f"{load_used}, in-plane is best); support proxy {chosen['support']:.1f} mm2 "
        f"overhang above {overhang_deg} deg with {chosen['bed_contact']:.1f} mm2 bed contact. "
        f"Selected strength-first among {len(candidates)} candidates, support as tiebreaker."
    )
    return {
        "rotate": _rotation_to_placement(chosen["rotation"]),
        "strength_score": chosen["strength"],
        "support_score": chosen["support"],
        "bed_contact_mm2": chosen["bed_contact"],
        "load_dir": load_used,
        "load_inferred": inferred,
        "rationale": rationale,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize a union's print orientation")
    parser.add_argument("stl", help="Union STL in its authored frame")
    parser.add_argument(
        "--overhang-max-deg",
        type=float,
        default=45.0,
        help="Overhang angle above which support is needed (plan constraint)",
    )
    parser.add_argument(
        "--load",
        default=None,
        help="Principal load direction 'x,y,z' in the authored frame; omit to infer",
    )
    args = parser.parse_args()

    load_dir = None
    if args.load:
        load_dir = [float(v) for v in args.load.split(",")]

    mesh = load_mesh(args.stl)
    result = optimize_orientation(mesh, args.overhang_max_deg, load_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
