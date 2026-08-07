#!/usr/bin/env python3
"""Kinematic range-of-motion validation stage.

`kinematics` entries nest into a tree via `children` (a joint's `children` are the
joints mounted on it). For each entry in the tree, at every nesting depth, verify the
joint achieves its author-declared range of motion:

  1. Numeric check (no mesh): the declared `required_range` (relative to the union's
     authored pose, so it may be negative or straddle zero) lies within a nominal
     mechanical limit -- the joint block's `dof.mechanical_limit` when the entry names a
     `block`, otherwise the entry's own `mechanical_limit` when declared. A block-less
     entry with no `mechanical_limit` reports the numeric arm as not applicable
     (`range_check_not_applicable`) rather than skipping silently, and still proceeds to
     the sweep below.
  2. Whole-model collision sweep (trimesh + fcl + manifold3d): step the entry's swept
     subtree -- its own moving union plus every union nested under its `children`,
     carried along rigidly by the same per-step transform -- through the required range
     against every union NOT in that subtree, each added as a separately named collision
     object so the colliding union is identifiable. A pose binds when the boolean
     intersection volume exceeds `penetration_tol_mm3` (designed surface contact at the
     joint is not interference). Bound inclusivity is honoured: a collision exactly at an
     open bound is not reported. A print-in-place joint (several unions on one plate) is
     swept the same way -- no special case.

     A cut-short sweep reports how far the joint actually got: the stopping value is
     bisected between the last clear and first binding swept value, so it does not depend
     on `step`, and the finding carries `achieved_range`, `min_clearance_mm`, and the
     overlap volume. An entry declaring `stop_on_contact` treats that first contact as the
     joint's MECHANICAL STOP rather than a defect -- the mechanism never reaches the
     interpenetrating poses beyond it -- so it emits a `contact_limited_stop` warning
     naming the shortfall instead of a `motion_collision` error.

Meshes are the assembled per-union STLs from `model_export.py` (placement already
applied), so `--stl-dir` points at that export. The inventory limit is a nominal
sanity bound; the sweep is authoritative for a specific assembled instance. Findings
use the shared quality-gate issue contract: `{source, severity, type, message,
hint, ...}`.

Usage:
    python3 kinematic_check.py --plan BUILD_PLAN.json --stl-dir dist
"""

import argparse
import os
from collections.abc import Iterator
from typing import Any

from freshness import read_manifest, stale_ids
from units import (
    add_parts_dir_argument,
    add_plan_argument,
    add_stl_dir_argument,
    emit_issues,
    load_plan,
    make_issue,
    stl_path,
)

_INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "blocks", "inventory.json")

_AXIS_VEC = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


def _unit_for(joint_type: str | None) -> str:
    """Derive the motion unit from the joint type: mm for prismatic, deg otherwise."""
    return "mm" if joint_type == "prismatic" else "deg"


# Azimuth samples around the cone for a spherical joint (v1: cone-boundary sampling,
# coarse -- a narrow interference between samples can be missed).
_SPHERICAL_AZIMUTHS_DEG = range(0, 360, 45)


def _sweep_values(
    lo: float, hi: float, step: float, lo_inc: bool = True, hi_inc: bool = True
) -> list[float]:
    """Sweep from lo to hi in `step` increments, honouring bound inclusivity.

    A closed bound (`*_inc=True`) is sampled; an open bound is excluded, so a
    collision exactly at an open endpoint is never evaluated. Interior samples are
    `lo + k*step` strictly between the bounds. Never steps past `hi`.
    """
    if hi <= lo:
        return [lo] if (lo_inc and hi_inc) else []
    values = []
    if lo_inc:
        values.append(lo)
    v = lo + step
    while v < hi - 1e-9:
        values.append(v)
        v += step
    if hi_inc:
        values.append(hi)
    return values


def _perpendicular(axis: Any) -> Any:
    """Return a unit vector perpendicular to `axis`."""
    import numpy as np

    a = np.asarray(axis, dtype=float)
    other = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    p = np.cross(a, other)
    return p / np.linalg.norm(p)


def travel_arms(entry: dict) -> list[list[float]]:
    """Split the entry's required range into arms of values, each ordered OUTWARD.

    The mechanism moves away from its authored pose (the zero), so the sweep must visit
    poses in that order -- otherwise "first interference" names an arbitrary sample
    rather than the joint's stop. A fold declared `[-90, 0]` swept lo->hi would start at
    -90, the deepest interpenetration, a pose reachable only through the joint's own
    stop.

    A wholly non-negative range is one ascending arm; a wholly non-positive range is one
    descending arm; a range straddling zero is two arms from zero (positive, negative)
    swept independently, so a stop on one side does not hide the other side.
    """
    lo, hi = entry["required_range"]
    step = entry["step"]
    lo_inc = entry.get("lo_inclusive", True)
    hi_inc = entry.get("hi_inclusive", True)
    values = _sweep_values(lo, hi, step, lo_inc, hi_inc)

    if lo >= 0:
        return [values]
    if hi <= 0:
        return [list(reversed(values))]
    zero = [v for v in values if abs(v) < 1e-9]
    positive = sorted(v for v in values if v > 1e-9)
    negative = sorted((v for v in values if v < -1e-9), reverse=True)
    return [zero + positive, zero + negative]


def _transforms_for(entry: dict, values: list[float]) -> Iterator[tuple[float, Any]]:
    """Yield (value, 4x4 transform) for each given swept value, in the order given.

    Revolute/prismatic yield one transform per value. Spherical yields one transform per
    azimuth at each cone half-angle.
    """
    import numpy as np
    from trimesh.transformations import rotation_matrix, translation_matrix

    jtype = entry["type"]
    axis = np.asarray(_AXIS_VEC[entry["axis_dir"]], dtype=float)
    origin = np.asarray(entry["axis_origin_mm"], dtype=float)

    if jtype == "revolute":
        for v in values:
            yield v, rotation_matrix(np.radians(v), axis, origin)
    elif jtype == "prismatic":
        for v in values:
            yield v, translation_matrix(axis * v)
    elif jtype == "spherical":
        base_perp = _perpendicular(axis)
        for v in values:
            if abs(v) < 1e-9:
                yield v, np.eye(4)
                continue
            for phi_deg in _SPHERICAL_AZIMUTHS_DEG:
                spin = rotation_matrix(np.radians(phi_deg), axis)[:3, :3]
                tilt_axis = spin @ base_perp
                yield v, rotation_matrix(np.radians(v), tilt_axis, origin)
    else:
        raise ValueError(f"Unsupported joint type: {jtype!r}")


def iter_poses(entry: dict) -> Iterator[tuple[float, Any]]:
    """Yield (value, 4x4 transform) poses spanning the entry's required range.

    Poses come in travel order (outward from the authored zero, see `travel_arms`),
    every arm concatenated. The sweep is bounded to `required_range`; no pose outside it
    is produced.
    """
    for arm in travel_arms(entry):
        yield from _transforms_for(entry, arm)


# Bisection refinement between the last clear and first binding swept value. Fixed count
# (step/256 resolution) rather than a tolerance loop: predictable cost, no knob, and well
# past the precision the mesh tessellation itself supports.
_BISECT_ITERATIONS = 8


def _interference_at(
    subtree_meshes: list[tuple[str, Any]],
    manager: Any,
    fixed_meshes: dict[str, Any],
    transform: Any,
    penetration_tol_mm3: float,
) -> dict[str, float]:
    """Overlap volume per fixed union for one pose of the whole swept subtree."""
    from interference import colliding_volumes

    hits: dict[str, float] = {}
    for _uid, mesh in subtree_meshes:
        moved = mesh.copy()
        moved.apply_transform(transform)
        for name, volume in colliding_volumes(
            moved, manager, penetration_tol_mm3, fixed_meshes
        ).items():
            hits[name] = max(hits.get(name, 0.0), volume)
    return hits


def _binds_at_value(
    subtree_meshes: list[tuple[str, Any]],
    manager: Any,
    fixed_meshes: dict[str, Any],
    entry: dict,
    value: float,
    penetration_tol_mm3: float,
) -> bool:
    """Whether any pose at a single swept value interferes (all azimuths, if spherical)."""
    return any(
        _interference_at(subtree_meshes, manager, fixed_meshes, transform, penetration_tol_mm3)
        for _v, transform in _transforms_for(entry, [value])
    )


def _min_clearance(subtree_meshes: list[tuple[str, Any]], manager: Any, transform: Any) -> float:
    """Smallest surface gap between the posed subtree and any fixed union."""
    gaps = []
    for _uid, mesh in subtree_meshes:
        moved = mesh.copy()
        moved.apply_transform(transform)
        gaps.append(manager.min_distance_single(moved))
    return min(gaps) if gaps else float("inf")


def _sweep_arm(
    subtree_meshes: list[tuple[str, Any]],
    manager: Any,
    fixed_meshes: dict[str, Any],
    entry: dict,
    values: list[float],
    penetration_tol_mm3: float,
) -> dict:
    """Sweep one arm (values already ordered outward from zero) and report where it ends.

    Returns `stop_value` (`None` if the arm swept clear -- then the arm's declared bound
    stands), `colliding`, `overlap_mm3`, and the `min_clearance_mm` observed over the
    travelled portion. A stop is bisected between the last clear and first binding value
    so it does not depend on `step`.
    """
    last_clear: float | None = None
    min_clearance = float("inf")

    for value, transform in _transforms_for(entry, values):
        hits = _interference_at(
            subtree_meshes, manager, fixed_meshes, transform, penetration_tol_mm3
        )
        if not hits:
            last_clear = value
            min_clearance = min(min_clearance, _min_clearance(subtree_meshes, manager, transform))
            continue

        stop_value = value
        if last_clear is not None:
            clear, binding = last_clear, value
            for _ in range(_BISECT_ITERATIONS):
                mid = (clear + binding) / 2.0
                if _binds_at_value(
                    subtree_meshes, manager, fixed_meshes, entry, mid, penetration_tol_mm3
                ):
                    binding = mid
                else:
                    clear = mid
            stop_value = clear
        return {
            "stop_value": stop_value,
            "colliding": sorted(hits),
            "overlap_mm3": round(max(hits.values()), 6),
            "min_clearance_mm": None if min_clearance == float("inf") else round(min_clearance, 4),
        }
    return {
        "stop_value": None,
        "colliding": [],
        "overlap_mm3": 0.0,
        "min_clearance_mm": None if min_clearance == float("inf") else round(min_clearance, 4),
    }


def _sweep_collision(
    subtree_meshes: list[tuple[str, Any]],
    manager: Any,
    fixed_meshes: dict[str, Any],
    entry: dict,
    penetration_tol_mm3: float,
) -> dict | None:
    """Sweep every mesh in the entry's subtree against a manager of named fixed unions.

    Each arm of the required range (see `travel_arms`) is swept independently outward
    from the authored zero, so a stop on one side does not hide the other side. The same
    per-step transform is applied identically to every subtree mesh (rigid carry-along: a
    descendant joint's own range is not composed in, it rides at its authored zero). The
    manager holds each fixed union as a separately named object so the colliding union is
    identifiable.

    Returns `None` when every arm sweeps clear. Otherwise returns the achieved range as
    `[achieved_lo, achieved_hi]` -- each bound either the declared bound (that side swept
    clear) or that side's bisected stop -- plus `stop_value` (the stop nearest the
    authored pose), `colliding`, `overlap_mm3`, and the smallest `min_clearance_mm` seen.
    """
    lo, hi = entry["required_range"]
    achieved = [lo, hi]
    stops: list[dict] = []
    clearances: list[float] = []

    for arm in travel_arms(entry):
        if not arm:
            continue
        result = _sweep_arm(subtree_meshes, manager, fixed_meshes, entry, arm, penetration_tol_mm3)
        if result["min_clearance_mm"] is not None:
            clearances.append(result["min_clearance_mm"])
        stop = result["stop_value"]
        if stop is None:
            continue
        # Which side this arm travelled decides which bound the stop replaces.
        if arm[-1] >= 0:
            achieved[1] = stop
        else:
            achieved[0] = stop
        stops.append(result)

    if not stops:
        return None

    nearest = min(stops, key=lambda r: abs(r["stop_value"]))
    return {
        "achieved_range": achieved,
        "stop_value": nearest["stop_value"],
        "colliding": sorted({name for r in stops for name in r["colliding"]}),
        "overlap_mm3": max(r["overlap_mm3"] for r in stops),
        "min_clearance_mm": min(clearances) if clearances else None,
    }


def run_kinematic_check(
    plan: dict,
    stl_dir: str,
    inventory_path: str = _INVENTORY_PATH,
    penetration_tol_mm3: float = 0.1,
    *,
    parts_dir: str | None = None,
) -> list[dict]:
    """Validate every `kinematics` entry in the plan, at every nesting depth. Returns a
    list of issues. When `parts_dir` is given and an export manifest is present, a union
    whose exported STL is stale relative to its current source script is flagged as
    `stale_artifact` and excluded from the sweep for any entry that references it. An
    entry with no `block` sources its mechanical limit from its own `mechanical_limit`
    field instead, or reports the numeric check as not applicable when neither is
    present; the sweep runs identically either way. An entry with `stop_on_contact` set
    reports first contact as its mechanical stop (`contact_limited_stop`, warning) rather
    than as a `motion_collision` error."""
    kinematics = plan.get("kinematics", [])
    if not kinematics:
        return []

    from blocks.validate import get_block

    issues: list[dict] = []

    # Collision backend is optional: the numeric check still runs without it.
    from interference import load_backend

    collision_ok = True
    try:
        load_backend()
    except ImportError as exc:
        collision_ok = False
        issues.append(
            make_issue(
                "kinematics",
                "warning",
                "check_skipped",
                f"Collision backend unavailable: {exc}",
                "Install python-fcl and scipy to enable the motion sweep.",
            )
        )

    from units import iter_kinematics_entries, iter_unions

    all_unions = [(part["id"], uid) for part, uid, _plate in iter_unions(plan)]
    all_union_ids = [uid for _pid, uid in all_unions]

    stale_unions: set[str] = set()
    if collision_ok:
        # Freshness only matters for the mesh sweep below; skip this check (and its own
        # warning) entirely when the sweep itself is already skipped for lack of a backend.
        manifest = read_manifest(stl_dir) if parts_dir else None
        if parts_dir is None or manifest is None:
            issues.append(
                make_issue(
                    "kinematics",
                    "warning",
                    "check_skipped",
                    "Export manifest not available; cannot verify exported STLs are current.",
                    "Run the model export (writes export_manifest.json) and pass "
                    "--parts-dir to enable staleness detection.",
                )
            )
        else:
            uid_to_script = {uid: os.path.join(parts_dir, f"{pid}.py") for pid, uid in all_unions}
            stale_unions = stale_ids(manifest.get("unions", {}), uid_to_script)

    for entry in iter_kinematics_entries(kinematics):
        jid = entry.get("joint_id", "(unknown)")
        unit = _unit_for(entry.get("type"))
        lo, hi = entry["required_range"]
        moving_id = entry["moving_union"]
        block = get_block(entry["block"], inventory_path) if entry.get("block") else None
        dof = (block or {}).get("dof")
        limit = dof["mechanical_limit"] if dof is not None else entry.get("mechanical_limit")

        # ---- numeric check (no mesh, no collision backend) ----
        if limit is not None:
            mlo, mhi = limit
            if lo < mlo - 1e-9 or hi > mhi + 1e-9:
                issues.append(
                    make_issue(
                        "kinematics",
                        "error",
                        "range_exceeds_limit",
                        f"Joint '{jid}' required range [{lo}, {hi}] {unit} exceeds "
                        f"mechanical limit [{mlo}, {mhi}] {unit}",
                        "Reduce the required range or choose a joint with a larger "
                        "mechanical limit.",
                        joint_id=jid,
                        required_range=[lo, hi],
                        mechanical_limit=[mlo, mhi],
                        unit=unit,
                    )
                )
                # Mechanically impossible: do not load a mesh or sweep this joint.
                continue
        else:
            issues.append(
                make_issue(
                    "kinematics",
                    "warning",
                    "range_check_not_applicable",
                    f"Joint '{jid}' has no mechanical_limit source (block-less entry "
                    "with none declared); numeric range check skipped, collision sweep "
                    "still runs.",
                    "Declare 'mechanical_limit' on the entry to enable the numeric check.",
                    joint_id=jid,
                )
            )

        # ---- collision sweep (subtree: moving union + everything nested under its
        # children, vs every union outside that subtree) ----
        if not collision_ok:
            continue

        import trimesh
        from trimesh.collision import CollisionManager

        subtree_ids = [e["moving_union"] for e in iter_kinematics_entries([entry])]
        fixed_ids = [uid for uid in all_union_ids if uid not in subtree_ids]

        stale_subtree = [uid for uid in subtree_ids if uid in stale_unions]
        stale_fixed = [uid for uid in fixed_ids if uid in stale_unions]
        if stale_subtree or stale_fixed:
            issues.append(
                make_issue(
                    "kinematics",
                    "error",
                    "stale_artifact",
                    f"Joint '{jid}': exported STL is stale for union(s) "
                    f"{', '.join(stale_subtree + stale_fixed)} -- the source script "
                    "changed since the model was last exported.",
                    "Re-run the model export so these unions' STLs reflect the current "
                    "scripts, then re-run the quality gate.",
                    joint_id=jid,
                    stale_unions=stale_subtree + stale_fixed,
                )
            )
            if stale_subtree:
                # The moving subtree itself is unreliable -- nothing meaningful to sweep.
                continue
            fixed_ids = [uid for uid in fixed_ids if uid not in stale_fixed]

        missing = [
            uid for uid in [*subtree_ids, *fixed_ids] if not os.path.exists(stl_path(stl_dir, uid))
        ]
        if missing:
            issues.append(
                make_issue(
                    "kinematics",
                    "warning",
                    "check_skipped",
                    f"Joint '{jid}': assembled union STL not found ({', '.join(missing)})",
                    "Run the model export so each union has an assembled STL.",
                    joint_id=jid,
                )
            )
            continue

        subtree_meshes = [
            (uid, trimesh.load(stl_path(stl_dir, uid), force="mesh")) for uid in subtree_ids
        ]
        manager = CollisionManager()
        fixed_meshes = {}
        for uid in fixed_ids:
            mesh = trimesh.load(stl_path(stl_dir, uid), force="mesh")
            manager.add_object(uid, mesh)
            fixed_meshes[uid] = mesh

        binding = _sweep_collision(
            subtree_meshes, manager, fixed_meshes, entry, penetration_tol_mm3
        )
        if binding is None:
            # Whole required range clear: achieved == required by definition, so no
            # finding. (The gate partitions on error/warning only; an informational
            # third tier would be silently discarded.)
            continue

        stop = binding["stop_value"]
        colliding = binding["colliding"]
        shared = {
            "joint_id": jid,
            "achieved_range": binding["achieved_range"],
            "colliding_union": colliding,
            "overlap_mm3": binding["overlap_mm3"],
            "min_clearance_mm": binding["min_clearance_mm"],
            "required_range": [lo, hi],
            "unit": unit,
        }

        if entry.get("stop_on_contact"):
            # Contact IS the design: the mechanism stops here and never reaches the
            # interpenetrating poses beyond, so this is not a defect. Report the stop and
            # let the designer judge the shortfall.
            issues.append(
                make_issue(
                    "kinematics",
                    "warning",
                    "contact_limited_stop",
                    f"Joint '{jid}' (moving union '{moving_id}') reaches "
                    f"{binding['achieved_range']} of the required [{lo}, {hi}] {unit}, "
                    f"stopping against {', '.join(colliding)}",
                    "If this stop is the intended rest position, narrow required_range to "
                    "match it; otherwise relieve the contacting feature.",
                    **shared,
                )
            )
        else:
            issues.append(
                make_issue(
                    "kinematics",
                    "error",
                    "motion_collision",
                    f"Joint '{jid}' (moving union '{moving_id}') binds at {stop} "
                    f"{unit} against {', '.join(colliding)} (required range "
                    f"[{lo}, {hi}] {unit}, achieved {binding['achieved_range']})",
                    "Increase joint clearance or relieve the colliding feature. If this "
                    "contact is the joint's intended mechanical stop, set "
                    "stop_on_contact.",
                    binding_value=stop,
                    **shared,
                )
            )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Kinematic range-of-motion validation")
    add_plan_argument(parser)
    add_stl_dir_argument(parser, "Directory holding exported <part_id>.stl files")
    add_parts_dir_argument(parser)
    parser.add_argument(
        "--penetration-tol-mm3",
        type=float,
        default=0.1,
        help="Intersection volume (mm^3) above which a pose counts as binding. Calibrated "
        "on a real fold (0.1 mm^3 puts the detected stop within ~0.5 deg of true "
        "tangency); raise it for curved mating faces whose tessellation overlaps more "
        "at nominal contact.",
    )
    parser.add_argument(
        "--inventory", default=_INVENTORY_PATH, help="Path to blocks/inventory.json"
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    issues = run_kinematic_check(
        plan,
        args.stl_dir,
        args.inventory,
        args.penetration_tol_mm3,
        parts_dir=args.parts_dir,
    )
    emit_issues(issues)


if __name__ == "__main__":
    main()
