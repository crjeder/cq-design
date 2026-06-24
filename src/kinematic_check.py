#!/usr/bin/env python3
"""Kinematic range-of-motion validation stage.

For each entry in a build plan's `kinematics` array, verify the joint achieves
its author-declared range of motion:

  1. Numeric check (no mesh): the declared `required_range` (relative to the union's
     authored pose, so it may be negative or straddle zero) lies within the joint
     block's nominal `dof.mechanical_limit` from the inventory.
  2. Whole-model collision sweep (trimesh + fcl): step the moving union through the
     required range against EVERY other union in the assembled model, each added as a
     separately named collision object so the colliding union is identifiable. Flag
     the first pose where penetration exceeds `penetration_tol_mm` (designed surface
     contact at the joint is not interference, so a small tolerance avoids false
     positives). Bound inclusivity is honoured: a collision exactly at an open bound
     is not reported. A print-in-place joint (several unions on one plate) is swept
     the same way -- no special case.

Meshes are the assembled per-union STLs from `model_export.py` (placement already
applied), so `--stl-dir` points at that export. The inventory limit is a nominal
sanity bound; the sweep is authoritative for a specific assembled instance. Findings
use the shared quality-gate issue contract: `{source, severity, type, message,
hint, ...}`.

Usage:
    python3 kinematic_check.py --plan BUILD_PLAN.json --stl-dir dist
"""

import argparse
import json
import os
import sys
from collections.abc import Iterator
from typing import Any

_INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "blocks", "inventory.json")

_AXIS_VEC = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}

# Azimuth samples around the cone for a spherical joint (v1: cone-boundary sampling,
# coarse -- a narrow interference between samples can be missed).
_SPHERICAL_AZIMUTHS_DEG = range(0, 360, 45)


def _issue(severity: str, type_: str, message: str, hint: str, **extra: Any) -> dict:
    """Build a finding in the shared quality-gate issue contract."""
    issue = {
        "source": "kinematics",
        "severity": severity,
        "type": type_,
        "message": message,
        "hint": hint,
    }
    issue.update(extra)
    return issue


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
    moving_mesh: Any, manager: Any, entry: dict, penetration_tol_mm: float
) -> tuple[float, list[str]] | None:
    """Sweep moving_mesh against a manager of named fixed unions.

    Returns (binding_value, sorted colliding union names) for the first pose whose
    deepest contact penetration exceeds penetration_tol_mm, or None if clear. The
    manager holds each fixed union as a separately named object so the colliding
    union is identifiable.
    """
    for value, transform in iter_poses(entry):
        moved = moving_mesh.copy()
        moved.apply_transform(transform)
        hit, names, data = manager.in_collision_single(moved, return_names=True, return_data=True)
        if hit:
            max_depth = max((abs(c.depth) for c in data), default=0.0)
            if max_depth > penetration_tol_mm:
                return value, sorted(names)
    return None


def _stl_path(stl_dir: str, part_id: str) -> str:
    return os.path.join(stl_dir, f"{part_id}.stl")


def run_kinematic_check(
    plan: dict,
    stl_dir: str,
    inventory_path: str = _INVENTORY_PATH,
    penetration_tol_mm: float = 0.1,
) -> list[dict]:
    """Validate every `kinematics` entry in the plan. Returns a list of issues."""
    kinematics = plan.get("kinematics", [])
    if not kinematics:
        return []

    from blocks.validate import get_block

    issues: list[dict] = []

    # Collision backend is optional: the numeric check still runs without it.
    collision_ok = True
    try:
        import fcl  # noqa: F401
        import trimesh  # noqa: F401
        from trimesh.collision import CollisionManager  # noqa: F401
    except ImportError as exc:
        collision_ok = False
        issues.append(
            _issue(
                "warning",
                "check_skipped",
                f"Collision backend unavailable: {exc}",
                "Install python-fcl and scipy to enable the motion sweep.",
            )
        )

    all_union_ids = [part.get("id") for part in plan.get("parts", [])]

    for entry in kinematics:
        jid = entry.get("joint_id", "(unknown)")
        unit = entry.get("unit")
        lo, hi = entry["required_range"]
        moving_id = entry["moving_union"]
        block = get_block(entry.get("block"), inventory_path)
        dof = (block or {}).get("dof")

        # ---- numeric check (no mesh, no collision backend) ----
        if dof is not None:
            mlo, mhi = dof["mechanical_limit"]
            if lo < mlo - 1e-9 or hi > mhi + 1e-9:
                issues.append(
                    _issue(
                        "error",
                        "range_exceeds_limit",
                        f"Joint '{jid}' required range [{lo}, {hi}] {unit} exceeds "
                        f"block mechanical limit [{mlo}, {mhi}] {dof.get('unit')}",
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

        # ---- collision sweep (whole model: moving union vs all other unions) ----
        if not collision_ok:
            continue

        import trimesh
        from trimesh.collision import CollisionManager

        moving_path = _stl_path(stl_dir, moving_id)
        fixed_ids = [uid for uid in all_union_ids if uid != moving_id]
        missing = [
            uid for uid in [moving_id, *fixed_ids] if not os.path.exists(_stl_path(stl_dir, uid))
        ]
        if missing:
            issues.append(
                _issue(
                    "warning",
                    "check_skipped",
                    f"Joint '{jid}': assembled union STL not found ({', '.join(missing)})",
                    "Run the model export so each union has an assembled STL.",
                    joint_id=jid,
                )
            )
            continue

        moving = trimesh.load(moving_path, force="mesh")
        manager = CollisionManager()
        for uid in fixed_ids:
            manager.add_object(uid, trimesh.load(_stl_path(stl_dir, uid), force="mesh"))

        binding = _sweep_collision(moving, manager, entry, penetration_tol_mm)
        if binding is not None:
            value, colliding = binding
            issues.append(
                _issue(
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
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument(
        "--stl-dir",
        required=True,
        help="Directory holding exported <part_id>.stl files",
    )
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

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    issues = run_kinematic_check(plan, args.stl_dir, args.inventory, args.penetration_tol)
    print(json.dumps({"issues": issues}, indent=2))
    has_error = any(i["severity"] == "error" for i in issues)
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
