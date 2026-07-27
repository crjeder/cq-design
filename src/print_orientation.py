#!/usr/bin/env python3
"""Print-orientation optimizer: choose how a union sits on the bed.

For a union mesh in its authored frame, enumerate stable bed-down orientations
(convex-hull resting facets + the six axis-aligned faces) and score each on:

  - strength: how well the part's load direction stays in the layer plane
    (perpendicular to build +Z). FDM is weakest ACROSS layers under tension,
    bending, or shear -- those stress the interlayer bond -- so for those load
    types a load that runs along Z is the worst case: Score = 1 - |load_after_rotation
    . Z|. Strength is orientation-neutral (1.0 for every pose, so support/bed-contact
    decide) when either no load is declared -- the optimizer does NOT guess a load
    axis from geometry; the planner declares `load.dir` (asking the user when the
    load path is unclear) -- or the declared `load.type` is COMPRESSION (a resting
    weight pressing straight down through a base/plinth/pedestal doesn't stress the
    interlayer bond). See `load` in `build_plan_schema.json` and `--load*` below.
  - support: downward-facing area above the overhang limit at that pose (a
    slicer-free proxy for support volume; less is better), with bed contact area as
    a tiebreaker (more contact prints more reliably).
  - visual: cosmetic-surface-down reward minus a gentle-incline penalty -- rewards
    orienting the declared/inferred `show_face` against the smooth bed and
    discounts shallow (under 45 deg) inclines that stair-step visibly.

Selection is mode-driven (`optimize_for`): `strength` (default) picks best strength
first; `min_support` picks least (severity-weighted) support first; `visual_quality`
picks best visual first; `min_build_height` picks the lowest posed profile first. Each
uses a tolerance band on its primary key with the remaining scores as deterministic
tiebreakers. The load and cosmetic directions are the part's declared `load.dir` /
`show_face.dir` when present and geometry-inferred otherwise.

The support score is a severity-weighted cost (steeper overhangs cost more), not a raw
overhang area; see `mesh_io.support_cost`.

The recommended orientation is emitted as a rotation in the placement.py
convention (ordered X/Y/Z steps), so the model export can apply it the same way
it applies a `placement`. It is distinct from the union's assembled-frame
`placement` and never overwrites it.

Usage:
    python3 print_orientation.py union.stl --overhang-max-deg 45
    python3 print_orientation.py union.stl --overhang-max-deg 45 --load 1,0,0
    python3 print_orientation.py union.stl --overhang-max-deg 45 \\
        --load 0,0,1 --load-type compression
    python3 print_orientation.py union.stl --optimize-for visual_quality \\
        --show-face 0,0,1
"""

import argparse
import json
import sys

import numpy as np
import trimesh
from trimesh.transformations import euler_from_matrix

from freshness import script_hash
from mesh_io import load_mesh, support_cost, up_facing_incline_area

# A candidate primary score within this band of the best is treated as tied, so the
# decision falls to the next key. Prevents jitter between near-identical poses.
STRENGTH_BAND = 0.02
# Support tie band used when minimizing support (weighted support-cost units).
SUPPORT_BAND = 1.0
# Visual-score tie band used when optimizing for visual quality.
VISUAL_BAND = 0.02
# Build-height tie band (mm) used when minimizing build height.
BUILD_HEIGHT_BAND_MM = 0.5
# Two bed-down normals within this angle are the same resting face.
NORMAL_MERGE_DEG = 5.0
# Face counts as bed contact when nearly flat-down and within one first-layer
# height of the floor (a marginally non-coplanar resting face still contacts).
FIRST_LAYER_BAND_MM = 0.3
# Severity exponent for the weighted support cost: > 1 so near-horizontal
# overhangs cost disproportionately more than ones just past the limit.
SUPPORT_EXPONENT = 2.0
# Area-dominant directions added as orientation candidates (top-N by area).
AREA_CUMULATION_TOP_N = 10
# Slopes shallower than this (from horizontal) are effectively flat: no stepping.
FLAT_EPS_DEG = 5.0
# Surfaces sloped under this from horizontal stair-step visibly (gentle inclines).
GENTLE_INCLINE_MAX_DEG = 45.0
# How heavily gentle-incline area discounts the cosmetic-face-down reward.
VISUAL_INCLINE_WEIGHT = 1.0
# Selectable print-orientation objectives.
OPTIMIZE_MODES = ("strength", "min_support", "visual_quality", "min_build_height")
# Load types recognized for strength scoring. tension/bending/shear all stress the
# interlayer bond and keep the existing layer-plane-alignment scoring; compression
# does not, so it scores as orientation-neutral (see _strength_score).
LOAD_TYPES = ("tension", "compression", "bending", "shear")
_DOWN = np.array([0.0, 0.0, -1.0])
_UP = np.array([0.0, 0.0, 1.0])
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


def _area_cumulation_normals(
    mesh: trimesh.Trimesh, top_n: int = AREA_CUMULATION_TOP_N
) -> list[np.ndarray]:
    """Top-N face directions by accumulated area (area-weighted normal buckets).

    Faces sharing a direction (within rounding) accumulate their areas; the
    directions carrying the most total area are the most likely stable resting
    faces. Returns up to `top_n` unit normals, most-area first. Cheap and
    bounded, complementing the convex-hull facets on dense/organic meshes where
    a large planar region may be split across many hull facets.
    """
    keys = np.round(mesh.face_normals, 2)
    buckets: dict[tuple, list] = {}
    for key, normal, area in zip(map(tuple, keys), mesh.face_normals, mesh.area_faces, strict=True):
        acc = buckets.get(key)
        if acc is None:
            buckets[key] = [float(area), normal * area]
        else:
            acc[0] += float(area)
            acc[1] = acc[1] + normal * area
    ranked = sorted(buckets.values(), key=lambda b: b[0], reverse=True)
    return [_unit(b[1]) for b in ranked[:top_n]]


def enumerate_candidate_normals(
    mesh: trimesh.Trimesh, merge_deg: float = NORMAL_MERGE_DEG
) -> list[np.ndarray]:
    """Bed-down normals to test: hull facets + 6 axis faces + area-dominant dirs.

    A part rests stably on a convex-hull face, so each unique hull-facet outward
    normal is a candidate "down" direction; the axis-aligned six are always
    included as a baseline; and the area-cumulation source adds directions that
    carry the most face area (catching large flat regions the hull may fragment).
    Normals within `merge_deg` are deduplicated so the set stays bounded.
    """
    normals: list[np.ndarray] = [n.copy() for n in _AXIS_NORMALS]
    try:
        hull_normals = mesh.convex_hull.face_normals
    except Exception:
        hull_normals = np.empty((0, 3))
    for n in hull_normals:
        normals.append(_unit(np.asarray(n, dtype=float)))
    normals.extend(_area_cumulation_normals(mesh))

    cos_tol = np.cos(np.radians(merge_deg))
    kept: list[np.ndarray] = []
    for n in normals:
        if not any(float(np.dot(n, k)) >= cos_tol for k in kept):
            kept.append(n)
    return kept


def _rotation_to_bed(down_normal: np.ndarray) -> np.ndarray:
    """4x4 rotation mapping `down_normal` to -Z (lays that face on the bed)."""
    return np.asarray(trimesh.geometry.align_vectors(_unit(down_normal), _DOWN))


def _strength_score(
    rotation: np.ndarray, load_dir: np.ndarray | None, load_type: str = "tension"
) -> float:
    """1.0 when the rotated load lies in the layer plane, 0.0 when along build Z.

    Strength is orientation-neutral (always 1.0, leaving support/bed-contact to
    decide) in two cases:
    - `load_dir is None`: no load was declared. The optimizer does NOT guess a load
      axis from geometry -- an undeclared load must not fabricate a bending
      direction and tip a flat part onto its edge. The planner is responsible for
      declaring `load.dir`/`load.type` (asking the user when the load path is
      unclear); an absent load is treated as "no strength preference", not a guess.
    - `load_type == "compression"`: a resting weight doesn't stress the interlayer
      bond regardless of orientation, so no pose is penalized.
    """
    if load_dir is None or load_type == "compression":
        return 1.0
    load_after = rotation[:3, :3] @ _unit(load_dir)
    return round(1.0 - abs(float(load_after[2])), 6)


def _support_metrics(posed: trimesh.Trimesh, overhang_deg: float) -> tuple[float, float]:
    """Return (support_cost, bed_contact_area) for the mesh already posed.

    The support cost is severity-weighted (steeper overhangs cost more; see
    `mesh_io.support_cost`); lower is better. The flat face resting on the bed is
    supported by the bed, not by support material, so it is excluded from the
    cost. Bed contact is counted within one first-layer height of the floor, so a
    marginally non-coplanar resting face still counts as contact.
    """
    min_z = float(posed.vertices[:, 2].min())
    centroids_z = posed.triangles.mean(axis=1)[:, 2]
    contact_mask = (posed.face_normals[:, 2] < -0.5) & (centroids_z <= min_z + FIRST_LAYER_BAND_MM)
    bed_contact = float(posed.area_faces[contact_mask].sum())
    cost = support_cost(posed, overhang_deg, SUPPORT_EXPONENT, exclude_mask=contact_mask)
    return round(cost, 3), round(bed_contact, 3)


def _infer_show_face(mesh: trimesh.Trimesh) -> np.ndarray:
    """Cosmetic surface guess: the outward normal of the largest planar facet.

    A part's most prominent flat face is the most likely "display" surface, so its
    outward normal (in the authored frame) is used as the cosmetic direction when
    the plan does not declare one. Falls back to the largest single triangle when
    the mesh has no coplanar facets.
    """
    facets = mesh.facets
    if len(facets):
        largest = int(np.argmax(mesh.facets_area))
        return _unit(np.asarray(mesh.facets_normal[largest], dtype=float))
    largest_tri = int(np.argmax(mesh.area_faces))
    return _unit(np.asarray(mesh.face_normals[largest_tri], dtype=float))


def _gentle_incline_fraction(posed: trimesh.Trimesh) -> float:
    """Fraction of visible face area that is a gentle (stair-stepping) incline.

    At the candidate pose, a face's slope from horizontal is the angle between its
    normal and the build axis Z (0 = flat top/bottom, 90 = vertical wall). Faces
    sloped within (FLAT_EPS_DEG, GENTLE_INCLINE_MAX_DEG) stair-step visibly in FDM;
    near-flat and near-vertical faces do not. Faces resting on the bed are excluded
    (not visible). Returns the bad-zone area over the total area (lower is better).
    """
    total = float(posed.area)
    if total <= 0.0:
        return 0.0

    nz = posed.face_normals[:, 2]
    slope = np.degrees(np.arccos(np.clip(np.abs(nz), 0.0, 1.0)))
    gentle = (slope > FLAT_EPS_DEG) & (slope < GENTLE_INCLINE_MAX_DEG)

    min_z = float(posed.vertices[:, 2].min())
    centroids_z = posed.triangles.mean(axis=1)[:, 2]
    on_bed = (nz < -0.5) & (centroids_z <= min_z + FIRST_LAYER_BAND_MM)

    bad_area = float(posed.area_faces[gentle & ~on_bed].sum())
    return round(bad_area / total, 6)


def _visual_metrics(
    posed: trimesh.Trimesh, rotation: np.ndarray, show_face_dir: np.ndarray
) -> tuple[float, float, float]:
    """Return (visual, cosmetic_down, gentle_incline_fraction) for the pose.

    `cosmetic_down` is how nearly the cosmetic surface faces the bed after rotation
    (1.0 straight down for the smoothest first-layer finish, 0.0 up or sideways).
    The visual score rewards that and discounts the gentle-incline area; higher is
    a more visually favorable orientation.
    """
    cosmetic_after = rotation[:3, :3] @ _unit(show_face_dir)
    cosmetic_down = max(0.0, float(np.dot(cosmetic_after, _DOWN)))
    incline = _gentle_incline_fraction(posed)
    visual = cosmetic_down - VISUAL_INCLINE_WEIGHT * incline
    return round(visual, 6), round(cosmetic_down, 6), incline


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


def _build_height(posed: trimesh.Trimesh) -> float:
    """Posed bounding-box extent along build Z (the print height at this pose)."""
    return round(float(posed.extents[2]), 3)


def _select(
    candidates: list[dict], optimize_for: str, strength_band: float = STRENGTH_BAND
) -> dict:
    """Pick a candidate by the requested optimization mode (lexicographic).

    Each mode chooses a primary score with a tolerance band so near-ties fall to
    the next key; `idx` is the final deterministic tiebreak in every mode.

    - strength: best strength, ties by least support, then most bed contact.
    - min_support: least support, ties by best strength, then most bed contact.
    - visual_quality: best visual, ties by best strength, then least support.
    - min_build_height: least build height, ties by best strength, then least support.
    """
    if optimize_for == "min_support":
        best = min(c["support"] for c in candidates)
        contenders = [c for c in candidates if c["support"] - best <= SUPPORT_BAND]
        return min(contenders, key=lambda c: (-c["strength"], -c["bed_contact"], c["idx"]))
    if optimize_for == "visual_quality":
        best = max(c["visual"] for c in candidates)
        contenders = [c for c in candidates if best - c["visual"] <= VISUAL_BAND]
        return min(contenders, key=lambda c: (-c["strength"], c["support"], c["idx"]))
    if optimize_for == "min_build_height":
        best = min(c["build_height"] for c in candidates)
        contenders = [c for c in candidates if c["build_height"] - best <= BUILD_HEIGHT_BAND_MM]
        return min(contenders, key=lambda c: (-c["strength"], c["support"], c["idx"]))

    best = max(c["strength"] for c in candidates)
    contenders = [c for c in candidates if best - c["strength"] <= strength_band]
    return min(contenders, key=lambda c: (c["support"], -c["bed_contact"], c["idx"]))


def optimize_orientation(
    mesh: trimesh.Trimesh,
    overhang_deg: float,
    load_dir: list[float] | None = None,
    strength_band: float = STRENGTH_BAND,
    optimize_for: str = "strength",
    show_face: list[float] | None = None,
    load_type: str = "tension",
) -> dict:
    """Choose the print orientation for a union mesh under the requested mode.

    `optimize_for` is one of `strength` (default), `min_support`,
    `visual_quality`, or `min_build_height`. `load_dir` is the principal load in
    the mesh's own frame and
    `show_face` is the cosmetic surface normal; both are inferred from geometry when
    None. `load_type` is one of `LOAD_TYPES`, default `tension`: `tension`/`bending`/
    `shear` keep the layer-plane-alignment strength scoring; `compression` makes
    strength orientation-neutral (see `_strength_score`) since a resting/compressive
    load doesn't stress the interlayer bond. Every candidate is scored on strength,
    support, and visual quality so the rationale can explain the trade-off
    regardless of mode. Returns the recommended rotation (placement convention), the
    score breakdown, the inputs used, and a human-readable rationale.
    """
    if optimize_for not in OPTIMIZE_MODES:
        raise ValueError(f"optimize_for must be one of {OPTIMIZE_MODES}, got {optimize_for!r}")
    if load_type not in LOAD_TYPES:
        raise ValueError(f"load_type must be one of {LOAD_TYPES}, got {load_type!r}")

    load_declared = load_dir is not None
    load_vec = np.asarray(load_dir, dtype=float) if load_declared else None
    show_face_inferred = show_face is None
    show_vec = _infer_show_face(mesh) if show_face_inferred else np.asarray(show_face, dtype=float)

    candidates = []
    for idx, normal in enumerate(enumerate_candidate_normals(mesh)):
        rotation = _rotation_to_bed(normal)
        posed = mesh.copy()
        posed.apply_transform(rotation)
        strength = _strength_score(rotation, load_vec, load_type)
        support, bed_contact = _support_metrics(posed, overhang_deg)
        visual, cosmetic_down, incline = _visual_metrics(posed, rotation, show_vec)
        candidates.append(
            {
                "idx": idx,
                "rotation": rotation,
                "strength": strength,
                "support": support,
                "bed_contact": bed_contact,
                "visual": visual,
                "cosmetic_down": cosmetic_down,
                "gentle_incline_fraction": incline,
                "build_height": _build_height(posed),
            }
        )

    chosen = _select(candidates, optimize_for, strength_band)

    # Cosmetic stair-step area at the chosen pose: up-facing faces in the gentle-incline
    # band. Reported by the quality gate (visual_quality only); distinct from the scoring
    # `gentle_incline_fraction` above (a both-faces fraction), which is left untouched.
    posed_chosen = mesh.copy()
    posed_chosen.apply_transform(chosen["rotation"])
    cosmetic_slope_area = up_facing_incline_area(posed_chosen, FLAT_EPS_DEG, GENTLE_INCLINE_MAX_DEG)

    load_used = [round(float(v), 6) for v in _unit(load_vec)] if load_vec is not None else None
    show_used = [round(float(v), 6) for v in _unit(show_vec)]
    rationale = _rationale(
        chosen, optimize_for, overhang_deg, len(candidates), load_type, load_declared
    )
    return {
        "optimize_for": optimize_for,
        "rotate": _rotation_to_placement(chosen["rotation"]),
        "strength_score": chosen["strength"],
        "support_score": chosen["support"],
        "bed_contact_mm2": chosen["bed_contact"],
        "visual_score": chosen["visual"],
        "cosmetic_down": chosen["cosmetic_down"],
        "gentle_incline_fraction": chosen["gentle_incline_fraction"],
        "cosmetic_slope_area_mm2": cosmetic_slope_area,
        "build_height_mm": chosen["build_height"],
        "load_dir": load_used,
        "load_declared": load_declared,
        "load_type": load_type,
        "show_face": show_used,
        "show_face_inferred": show_face_inferred,
        "rationale": rationale,
    }


def _rationale(
    chosen: dict,
    optimize_for: str,
    overhang_deg: float,
    n_candidates: int,
    load_type: str = "tension",
    load_declared: bool = True,
) -> str:
    """Human-readable explanation naming the mode and the winning trade-off."""
    common = (
        f"strength {chosen['strength']:.3f}, weighted support-cost "
        f"{chosen['support']:.1f} (overhang above {overhang_deg} deg), build height "
        f"{chosen['build_height']:.1f} mm, visual {chosen['visual']:.3f} "
        f"(cosmetic-down {chosen['cosmetic_down']:.2f}, "
        f"{chosen['gentle_incline_fraction'] * 100:.0f}% gentle-incline area)"
    )
    if not load_declared:
        common += (
            ". no load declared: strength is orientation-neutral (the optimizer does not "
            "guess a load axis), so support/bed-contact decided -- declare load.dir in the "
            "plan if this part carries a real tension/bending/shear load"
        )
    elif load_type == "compression":
        common += (
            ". load_type=compression: strength is orientation-neutral "
            "(interlayer bond isn't stressed by a resting load), so support/bed-contact decided"
        )
    if optimize_for == "min_support":
        lead = "min_support: least support first, strength as tiebreaker"
    elif optimize_for == "visual_quality":
        lead = "visual_quality: best appearance first, strength then support as tiebreakers"
    elif optimize_for == "min_build_height":
        lead = "min_build_height: lowest profile first, strength then support as tiebreakers"
    else:
        lead = "strength: layer-plane strength first, support as tiebreaker"
    return f"{lead}. Chosen among {n_candidates} candidates: {common}."


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
        help="Principal load direction 'x,y,z' in the authored frame; omit for a "
        "strength-neutral part (no load axis is guessed)",
    )
    parser.add_argument(
        "--load-type",
        choices=LOAD_TYPES,
        default="tension",
        help=(
            "Load type (default: tension). tension/bending/shear keep layer-plane "
            "strength scoring; compression (a resting weight pressing straight "
            "down, e.g. a base/plinth/pedestal) makes strength orientation-neutral."
        ),
    )
    parser.add_argument(
        "--optimize-for",
        choices=OPTIMIZE_MODES,
        default="strength",
        help="Orientation objective (default: strength)",
    )
    parser.add_argument(
        "--show-face",
        default=None,
        help="Cosmetic surface normal 'x,y,z' in the authored frame; omit to infer",
    )
    parser.add_argument(
        "--source-script",
        default=None,
        help="Part script that produced this STL; when given, the result is stamped with "
        "the script's provenance hash (source_script_hash) so a consumer can detect a "
        "later edit. Omit to leave the result unstamped.",
    )
    args = parser.parse_args()

    load_dir = None
    if args.load:
        load_dir = [float(v) for v in args.load.split(",")]
    show_face = None
    if args.show_face:
        show_face = [float(v) for v in args.show_face.split(",")]

    mesh = load_mesh(args.stl)
    result = optimize_orientation(
        mesh,
        args.overhang_max_deg,
        load_dir,
        optimize_for=args.optimize_for,
        show_face=show_face,
        load_type=args.load_type,
    )
    if args.source_script:
        result["source_script_hash"] = script_hash(args.source_script)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
