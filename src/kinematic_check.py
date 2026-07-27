#!/usr/bin/env python3
"""Kinematic range-of-motion validation stage.

`kinematics` entries nest into a tree via `children` (a joint's `children` are the
joints mounted on it). For each entry in the tree, at every nesting depth, verify the
joint achieves its author-declared range of motion:

  1. Numeric check (no mesh): the declared `required_range` (relative to the union's
     authored pose, so it may be negative or straddle zero) lies within the joint
     block's nominal `dof.mechanical_limit` from the inventory.
  2. Whole-model collision sweep (trimesh + fcl): step the entry's swept subtree --
     its own moving union plus every union nested under its `children`, carried along
     rigidly by the same per-step transform -- through the required range against
     every union NOT in that subtree, each added as a separately named collision
     object so the colliding union is identifiable. Flag the first pose where
     penetration exceeds `penetration_tol_mm` (designed surface contact at the joint
     is not interference, so a small tolerance avoids false positives). Bound
     inclusivity is honoured: a collision exactly at an open bound is not reported. A
     print-in-place joint (several unions on one plate) is swept the same way -- no
     special case.

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


def iter_poses(entry: dict) -> Iterator[tuple[float, Any]]:
    """Yield (value, 4x4 transform) poses spanning the entry's required range.

    Revolute/prismatic yield one transform per swept value. Spherical yields one
    transform per azimuth at each swept cone half-angle. The sweep is bounded to
    `required_range`; no pose beyond `required_range[1]` is produced.
    """
    import numpy as np
    from trimesh.transformations import rotation_matrix, translation_matrix

    jtype = entry["type"]
    axis = np.asarray(_AXIS_VEC[entry["axis_dir"]], dtype=float)
    origin = np.asarray(entry["axis_origin_mm"], dtype=float)
    lo, hi = entry["required_range"]
    step = entry["step"]
    lo_inc = entry.get("lo_inclusive", True)
    hi_inc = entry.get("hi_inclusive", True)

    if jtype == "revolute":
        for v in _sweep_values(lo, hi, step, lo_inc, hi_inc):
            yield v, rotation_matrix(np.radians(v), axis, origin)
    elif jtype == "prismatic":
        for v in _sweep_values(lo, hi, step, lo_inc, hi_inc):
            yield v, translation_matrix(axis * v)
    elif jtype == "spherical":
        base_perp = _perpendicular(axis)
        for v in _sweep_values(lo, hi, step, lo_inc, hi_inc):
            if abs(v) < 1e-9:
                yield v, np.eye(4)
                continue
            for phi_deg in _SPHERICAL_AZIMUTHS_DEG:
                spin = rotation_matrix(np.radians(phi_deg), axis)[:3, :3]
                tilt_axis = spin @ base_perp
                yield v, rotation_matrix(np.radians(v), tilt_axis, origin)
    else:
        raise ValueError(f"Unsupported joint type: {jtype!r}")


def _sweep_collision(
    subtree_meshes: list[tuple[str, Any]], manager: Any, entry: dict, penetration_tol_mm: float
) -> tuple[float, list[str]] | None:
    """Sweep every mesh in the entry's subtree against a manager of named fixed unions.

    The same per-step transform is applied identically to every subtree mesh (rigid
    carry-along: a descendant joint's own range is not composed in, it rides at its
    authored zero). Returns (binding_value, sorted colliding union names) for the first
    pose where any subtree member's deepest contact penetration exceeds
    penetration_tol_mm, or None if clear. The manager holds each fixed union as a
    separately named object so the colliding union is identifiable.
    """
    from interference import colliding_names

    for value, transform in iter_poses(entry):
        colliding: set[str] = set()
        for _uid, mesh in subtree_meshes:
            moved = mesh.copy()
            moved.apply_transform(transform)
            colliding |= colliding_names(moved, manager, penetration_tol_mm)
        if colliding:
            return value, sorted(colliding)
    return None


def run_kinematic_check(
    plan: dict,
    stl_dir: str,
    inventory_path: str = _INVENTORY_PATH,
    penetration_tol_mm: float = 0.1,
    *,
    parts_dir: str | None = None,
) -> list[dict]:
    """Validate every `kinematics` entry in the plan, at every nesting depth. Returns a
    list of issues. When `parts_dir` is given and an export manifest is present, a union
    whose exported STL is stale relative to its current source script is flagged as
    `stale_artifact` and excluded from the sweep for any entry that references it."""
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
        block = get_block(entry["block"], inventory_path)
        dof = (block or {}).get("dof")

        # ---- numeric check (no mesh, no collision backend) ----
        if dof is not None:
            mlo, mhi = dof["mechanical_limit"]
            if lo < mlo - 1e-9 or hi > mhi + 1e-9:
                issues.append(
                    make_issue(
                        "kinematics",
                        "error",
                        "range_exceeds_limit",
                        f"Joint '{jid}' required range [{lo}, {hi}] {unit} exceeds "
                        f"block mechanical limit [{mlo}, {mhi}] {unit}",
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
        for uid in fixed_ids:
            manager.add_object(uid, trimesh.load(stl_path(stl_dir, uid), force="mesh"))

        binding = _sweep_collision(subtree_meshes, manager, entry, penetration_tol_mm)
        if binding is not None:
            value, colliding = binding
            issues.append(
                make_issue(
                    "kinematics",
                    "error",
                    "motion_collision",
                    f"Joint '{jid}' (moving union '{moving_id}') binds at {value} "
                    f"{unit} against {', '.join(colliding)} (required up to {hi} {unit})",
                    "Increase joint clearance or relieve the colliding feature.",
                    joint_id=jid,
                    binding_value=value,
                    colliding_union=colliding,
                    required_range=[lo, hi],
                    unit=unit,
                )
            )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Kinematic range-of-motion validation")
    add_plan_argument(parser)
    add_stl_dir_argument(parser, "Directory holding exported <part_id>.stl files")
    add_parts_dir_argument(parser)
    parser.add_argument(
        "--penetration-tol",
        type=float,
        default=0.1,
        help="Contact penetration depth (mm) above which a pose counts as binding",
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
        args.penetration_tol,
        parts_dir=args.parts_dir,
    )
    emit_issues(issues)


if __name__ == "__main__":
    main()
