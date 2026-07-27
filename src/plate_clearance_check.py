#!/usr/bin/env python3
"""Plate-clearance validation stage.

When two or more unions share a plate (print-in-place), they print in one job at fixed
relative positions. If any pair comes closer than one layer height anywhere, the slicer
bridges the gap and they fuse into one solid -- a working joint locks up, or two parts
meant to separate come out as one.

`model_export` fuses each plate as a rigid cluster: the unions keep their assembled
relative transforms and the whole cluster is rotated together into print orientation. A
rigid rotation preserves distances, so the minimum surface-to-surface gap between two
co-plated unions is identical in the assembled pose and in print orientation. This stage
therefore measures the gap on the assembled per-union STLs `model_export.py` already emits
for the kinematic check (placement applied), with no new export and no print-orientation
bookkeeping.

The threshold is one layer height, derived the same way the gate derives `layer_height_mm`
for its print recipe (`nozzle_mm * 0.5`). A pair passes only when its gap is strictly
greater than the threshold; a gap at or below it is flagged as a `plate_clearance` error.
Findings use the shared quality-gate issue contract: `{source, severity, type, message,
hint, ...}`.

Usage:
    python3 plate_clearance_check.py --plan BUILD_PLAN.json --stl-dir dist
"""

import os
from itertools import combinations
from typing import cast

from freshness import read_manifest, stale_ids
from units import iter_unions, make_issue, run_stl_dir_check_cli, stl_path


def _plates_with_multiple_unions(plan: dict) -> dict[str, list[str]]:
    """Group union ids by plate, keeping only plates that hold more than one union.

    Uses the shared `units.iter_unions` expansion so a multi-union part's unions are grouped
    by their own plate, agreeing with the exporter on which unions are co-plated.
    """
    plates: dict[str, list[str]] = {}
    for _part, uid, plate in iter_unions(plan):
        plates.setdefault(plate, []).append(uid)
    return {plate: ids for plate, ids in plates.items() if len(ids) > 1}


def run_plate_clearance_check(
    plan: dict, stl_dir: str, *, parts_dir: str | None = None
) -> list[dict]:
    """Check that every pair of co-plated unions keeps a gap above one layer height.

    Returns a list of issues. Plates holding a single union are skipped; when no plate
    holds more than one union, returns an empty list without loading the geometry stack.
    When `parts_dir` is given and an export manifest is present, a union whose exported
    STL is stale relative to its current source script is flagged as `stale_artifact` and
    excluded from the pairwise comparison (a plate with fewer than two fresh unions left
    is skipped, not fused-checked against superseded geometry).
    """
    plates = _plates_with_multiple_unions(plan)
    if not plates:
        return []

    # Geometry backend is optional, matching the kinematic check's degrade path.
    try:
        import trimesh
        from trimesh.collision import CollisionManager
    except ImportError as exc:
        return [
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                f"Geometry backend unavailable for plate-clearance check: {exc}",
                "Install trimesh and python-fcl to enable the plate-clearance check.",
            )
        ]

    nozzle = plan.get("nozzle_mm", 0.4)
    threshold = round(nozzle * 0.5, 2)  # one layer height, as in the print recipe

    issues: list[dict] = []

    manifest = read_manifest(stl_dir) if parts_dir else None
    if parts_dir is None or manifest is None:
        issues.append(
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                "Export manifest not available; cannot verify exported STLs are current.",
                "Run the model export (writes export_manifest.json) and pass --parts-dir "
                "to enable staleness detection.",
            )
        )
        stale: set[str] = set()
    else:
        plated_ids = {uid for ids in plates.values() for uid in ids}
        uid_to_script = {
            uid: os.path.join(parts_dir, f"{part['id']}.py")
            for part, uid, _plate in iter_unions(plan)
            if uid in plated_ids
        }
        stale = stale_ids(manifest.get("unions", {}), uid_to_script)

    for plate, ids in plates.items():
        for uid in ids:
            if uid in stale:
                issues.append(
                    make_issue(
                        "geometry",
                        "error",
                        "stale_artifact",
                        f"Union '{uid}' on plate '{plate}': exported STL is stale -- its "
                        "source script changed since the model was last exported.",
                        "Re-run the model export so this union's STL reflects the current "
                        "script, then re-run the quality gate.",
                        plate=plate,
                        union=uid,
                    )
                )
        ids = [uid for uid in ids if uid not in stale]
        if len(ids) < 2:
            continue

        missing = [uid for uid in ids if not os.path.exists(stl_path(stl_dir, uid))]
        if missing:
            issues.append(
                make_issue(
                    "geometry",
                    "warning",
                    "check_skipped",
                    f"Plate '{plate}': assembled union STL not found ({', '.join(missing)})",
                    "Run the model export so each union has an assembled STL.",
                    plate=plate,
                )
            )
            continue

        meshes = {uid: trimesh.load(stl_path(stl_dir, uid), force="mesh") for uid in ids}
        for a, b in combinations(ids, 2):
            manager = CollisionManager()
            manager.add_object(a, meshes[a])
            # No return flags -> min_distance_single returns the scalar distance.
            gap = round(cast(float, manager.min_distance_single(meshes[b])), 3)
            if gap <= threshold:
                issues.append(
                    make_issue(
                        "geometry",
                        "error",
                        "plate_clearance",
                        f"Unions '{a}' and '{b}' on plate '{plate}' are {gap} mm apart "
                        f"(<= {threshold} mm layer height); they will fuse in the print.",
                        "Increase the gap between these unions to more than one layer "
                        "height, or move one to a separate plate.",
                        plate=plate,
                        union_a=a,
                        union_b=b,
                        gap_mm=gap,
                        threshold_mm=threshold,
                    )
                )

    return issues


def main() -> None:
    run_stl_dir_check_cli(
        "Plate-clearance validation",
        "Directory holding exported assembled <part_id>.stl files",
        run_plate_clearance_check,
    )


if __name__ == "__main__":
    main()
