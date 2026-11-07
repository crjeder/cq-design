#!/usr/bin/env python3
"""All-pairs rest-pose interference stage.

Tests every pair of unions' assembled-pose STLs (`write_assembly.py`) for overlap, so a lid
sitting inside its box fails the gate without any joint, kinematics entry or keep-out zone
being declared. fcl (via `CollisionManager.in_collision_internal`) is the broadphase; the
boolean intersection volume is measured only for touching pairs, and a pair counts when it
exceeds `OVERLAP_TOL_MM3` -- the same epsilon `kinematic_check` and `plate_clearance_check`
use, so flush designed contact never reads as interference.

Skipped pairs:
- co-plated unions: `plate_clearance_check` already rejects them at or below a layer height
  of gap, which includes any overlap;
- press-fit joint members: the two unions of a `joints` entry whose `params.clearance` is
  negative, plus every `copy_of` copy of either member's part.

Findings use the shared quality-gate issue contract: `{source, severity, type, message,
hint, ...}`.

Usage:
    python3 assembly_interference_check.py --plan BUILD_PLAN.json --stl-dir dist
"""

import os
from itertools import product
from typing import Any

from freshness import read_manifest, script_stem, stale_ids
from interference import _intersection_volume, load_backend
from units import (
    iter_unions,
    make_issue,
    member_union,
    run_stl_dir_check_cli,
    stl_path,
)

OVERLAP_TOL_MM3 = 0.1


def press_fit_pairs(plan: dict) -> set[frozenset[str]]:
    """Union-id pairs exempt as press fits: members of a joint with negative `clearance`.

    A `copy_of` part inherits the exemption of its source part's member union.
    # ponytail: copies on both sides also exempt peg copy 1 vs hole copy 2, not only the
    # pairs that mate; tighten once copies carry their own joint mapping.
    """
    parts = {p["id"]: p for p in plan.get("parts", [])}
    copies_of: dict[str, list[str]] = {}
    for p in parts.values():
        if p.get("copy_of"):
            copies_of.setdefault(p["copy_of"]["part"], []).append(p["id"])

    exempt: set[frozenset[str]] = set()
    for joint in plan.get("joints", []):
        if joint.get("params", {}).get("clearance", 0) >= 0:
            continue
        sides = []
        for m in joint["members"]:
            part = parts.get(m["part"])
            uid = member_union(part, m) if part else None
            if uid is None:
                break
            sides.append([uid, *copies_of.get(m["part"], [])])
        else:
            exempt.update(frozenset(pair) for pair in product(*sides))
    return exempt


def _stale_union_ids(
    plan: dict, stl_dir: str, parts_dir: str | None
) -> tuple[set[str], dict | None]:
    """Returns (stale union ids, warning issue if the manifest is unavailable)."""
    manifest = read_manifest(stl_dir) if parts_dir else None
    if parts_dir is None or manifest is None:
        return set(), make_issue(
            "geometry",
            "warning",
            "check_skipped",
            "Export manifest not available; cannot verify exported STLs are current.",
            "Run the model export (writes export_manifest.json) and pass --parts-dir "
            "to enable staleness detection.",
        )
    unions_section = manifest.get("unions", {})
    uid_to_script = {
        uid: os.path.join(parts_dir, f"{script_stem(unions_section, uid, part['id'])}.py")
        for part, uid, _plate in iter_unions(plan)
    }
    return stale_ids(unions_section, uid_to_script), None


def _overlap_issue(a: str, b: str, volume: float) -> dict:
    return make_issue(
        "geometry",
        "error",
        "assembly_interference",
        f"Unions '{a}' and '{b}' overlap by {volume} mm^3 in the assembled pose.",
        f"Move or trim '{a}' / '{b}' so they only touch. If the overlap is an intended "
        "press fit, declare the pair in `joints` with a negative `params.clearance`.",
        union_a=a,
        union_b=b,
        overlap_mm3=volume,
    )


def run_assembly_interference_check(
    plan: dict, stl_dir: str, *, parts_dir: str | None = None
) -> list[dict]:
    """Check every pair of unions for rest-pose overlap above `OVERLAP_TOL_MM3`."""
    unions = iter_unions(plan)
    if len(unions) < 2:
        return []

    try:
        trimesh, collision_manager_cls = load_backend()
    except ImportError as exc:
        return [
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                f"Geometry backend unavailable for assembly-interference check: {exc}",
                "Install trimesh, python-fcl and manifold3d to enable the check.",
            )
        ]

    issues: list[dict] = []
    stale, staleness_issue = _stale_union_ids(plan, stl_dir, parts_dir)
    if staleness_issue:
        issues.append(staleness_issue)
    for _part, uid, _plate in unions:
        if uid in stale:
            issues.append(
                make_issue(
                    "geometry",
                    "error",
                    "stale_artifact",
                    f"Union '{uid}': exported STL is stale -- its source script changed "
                    "since the model was last exported.",
                    "Re-run the model export so this union's STL reflects the current "
                    "script, then re-run the quality gate.",
                    union=uid,
                )
            )

    live = [(uid, plate) for _part, uid, plate in unions if uid not in stale]
    missing = [uid for uid, _plate in live if not os.path.exists(stl_path(stl_dir, uid))]
    if missing:
        issues.append(
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                f"Assembly-interference check: assembled union STL not found "
                f"({', '.join(missing)})",
                "Run the model export so each union has an assembled STL.",
            )
        )
        return issues

    plate_of_union = dict(live)
    meshes: dict[str, Any] = {
        uid: trimesh.load(stl_path(stl_dir, uid), force="mesh") for uid, _plate in live
    }
    manager = collision_manager_cls()
    for uid, mesh in meshes.items():
        manager.add_object(uid, mesh)

    exempt = press_fit_pairs(plan)
    _hit, pairs = manager.in_collision_internal(return_names=True)
    for a, b in sorted(tuple(sorted(p)) for p in pairs):
        if plate_of_union[a] == plate_of_union[b] or frozenset((a, b)) in exempt:
            continue
        volume = round(_intersection_volume(meshes[a], meshes[b]), 3)
        if volume > OVERLAP_TOL_MM3:
            issues.append(_overlap_issue(a, b, volume))
    return issues


def main() -> None:
    run_stl_dir_check_cli(
        "All-pairs rest-pose interference validation",
        "Directory holding exported <union_id>.stl files",
        run_assembly_interference_check,
    )


if __name__ == "__main__":
    main()
