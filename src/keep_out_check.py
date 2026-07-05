#!/usr/bin/env python3
"""Keep-out-zone validation stage.

A part's script may declare one or more named keep-out zones (the reserved `keep_out`
result key -- see `units.resolve_keep_out`). `model_export.export_model` poses each zone
the same way as its declaring part's real unions and writes it to its own assembled-pose
STL, named by `units.keep_out_stl_name`, alongside the per-union STLs it already produces.

This stage discovers every such STL in `--stl-dir` by that naming convention (no
plan-schema field names a zone -- it is discovered from export output, like a part's
declared unions), then tests each zone's mesh for intersection against every union in the
model, EXCLUDING the zone's own declaring part's unions (a zone is typically anchored
flush against the very feature it protects). Any intrusion is a hard reject: findings use
the shared quality-gate issue contract: `{source, severity, type, message, hint, ...}`.

Usage:
    python3 keep_out_check.py --plan BUILD_PLAN.json --stl-dir dist
"""

import argparse
import glob
import json
import os
import sys
from typing import Any, cast

from units import KEEP_OUT_KEY

_ZONE_PREFIX = f"{KEEP_OUT_KEY}__"


def _issue(severity: str, type_: str, message: str, hint: str, **extra: Any) -> dict:
    """Build a finding in the shared quality-gate issue contract."""
    issue = {
        "source": "geometry",
        "severity": severity,
        "type": type_,
        "message": message,
        "hint": hint,
    }
    issue.update(extra)
    return issue


def _stl_path(stl_dir: str, union_id: str) -> str:
    return os.path.join(stl_dir, f"{union_id}.stl")


def _discover_zones(plan: dict, stl_dir: str) -> list[tuple[str, str, str]]:
    """Find every declared zone's STL in `stl_dir` via the `keep_out__` naming convention.

    Returns `(declaring_part_id, zone_name, stl_path)` tuples. A zone's declaring part is
    resolved by longest-prefix match against the plan's known part ids, so a zone name may
    itself contain "__" without ambiguity in the common case.
    """
    part_ids = sorted((p["id"] for p in plan.get("parts", [])), key=len, reverse=True)
    zones: list[tuple[str, str, str]] = []
    for path in glob.glob(os.path.join(stl_dir, f"{_ZONE_PREFIX}*.stl")):
        stem = os.path.splitext(os.path.basename(path))[0]
        rest = stem[len(_ZONE_PREFIX) :]
        for pid in part_ids:
            marker = pid + "__"
            if rest.startswith(marker):
                zones.append((pid, rest[len(marker) :], path))
                break
    return zones


def run_keep_out_check(plan: dict, stl_dir: str) -> list[dict]:
    """Check every declared keep-out zone against every foreign union. Returns issues.

    Returns an empty list without loading the geometry stack when the model declares no
    keep-out zones (regardless of whether the collision backend is available).
    """
    zones = _discover_zones(plan, stl_dir)
    if not zones:
        return []

    # Geometry backend is optional, matching the kinematic/plate-clearance checks' degrade path.
    try:
        import trimesh
        from trimesh.collision import CollisionManager
    except ImportError as exc:
        return [
            _issue(
                "warning",
                "check_skipped",
                f"Geometry backend unavailable for keep-out check: {exc}",
                "Install trimesh and python-fcl to enable the keep-out check.",
            )
        ]

    from units import iter_unions

    all_unions = [(part.get("id"), uid) for part, uid, _plate in iter_unions(plan)]

    issues: list[dict] = []
    for declaring_part, zone_name, zone_path in zones:
        fixed = [(pid, uid) for pid, uid in all_unions if pid != declaring_part]
        missing = [uid for _pid, uid in fixed if not os.path.exists(_stl_path(stl_dir, uid))]
        if missing:
            issues.append(
                _issue(
                    "warning",
                    "check_skipped",
                    f"Keep-out zone '{zone_name}' (part '{declaring_part}'): assembled union "
                    f"STL not found ({', '.join(missing)})",
                    "Run the model export so each union has an assembled STL.",
                    zone_part=declaring_part,
                    zone_name=zone_name,
                )
            )
            continue

        zone_mesh = trimesh.load(zone_path, force="mesh")
        manager = CollisionManager()
        for _pid, uid in fixed:
            manager.add_object(uid, trimesh.load(_stl_path(stl_dir, uid), force="mesh"))

        hit, names, _data = cast(
            "tuple[bool, set[str], list[Any]]",
            manager.in_collision_single(zone_mesh, return_names=True, return_data=True),
        )
        if hit:
            for uid in sorted(names):
                issues.append(
                    _issue(
                        "error",
                        "keep_out_violation",
                        f"Union '{uid}' intrudes on keep-out zone '{zone_name}' declared by "
                        f"part '{declaring_part}'",
                        f"Redesign '{uid}' so it clears keep-out zone '{zone_name}' (declared "
                        f"by part '{declaring_part}'); the zone itself is a note-to-self, not "
                        "the thing to change.",
                        zone_part=declaring_part,
                        zone_name=zone_name,
                        offending_union=uid,
                    )
                )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep-out-zone validation")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument(
        "--stl-dir",
        required=True,
        help="Directory holding exported <union_id>.stl and keep_out__*.stl files",
    )
    args = parser.parse_args()

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    issues = run_keep_out_check(plan, args.stl_dir)
    print(json.dumps({"issues": issues}, indent=2))
    has_error = any(i["severity"] == "error" for i in issues)
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
