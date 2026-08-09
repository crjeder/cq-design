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

import glob
import os
from collections.abc import Callable
from typing import Any

from freshness import read_manifest, stale_ids
from units import KEEP_OUT_KEY, iter_unions, make_issue, run_stl_dir_check_cli, stl_path

_ZONE_PREFIX = f"{KEEP_OUT_KEY}__"


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


def _load_geometry_backend() -> tuple[Any, Callable[..., set[str]] | None, dict | None]:
    """Try to load the geometry backend. Returns (trimesh, check_interference, issue)."""
    from interference import check_interference, load_backend

    try:
        trimesh, _ = load_backend()
        return trimesh, check_interference, None
    except ImportError as exc:
        return (
            None,
            None,
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                f"Geometry backend unavailable for keep-out check: {exc}",
                "Install trimesh and python-fcl to enable the keep-out check.",
            ),
        )


def _compute_staleness(
    all_unions: list[tuple[str | None, str]],
    zones: list[tuple[str, str, str]],
    stl_dir: str,
    parts_dir: str | None,
) -> tuple[set[str], set[str], dict | None]:
    """Returns (stale union ids, stale zone keys, warning issue if manifest unavailable)."""
    manifest = read_manifest(stl_dir) if parts_dir else None
    if parts_dir is None or manifest is None:
        return (
            set(),
            set(),
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                "Export manifest not available; cannot verify exported STLs are current.",
                "Run the model export (writes export_manifest.json) and pass --parts-dir "
                "to enable staleness detection.",
            ),
        )

    uid_to_script = {uid: os.path.join(parts_dir, f"{pid}.py") for pid, uid in all_unions}
    stale_unions = stale_ids(manifest.get("unions", {}), uid_to_script)
    zone_to_script = {
        f"{declaring_part}::{zone_name}": os.path.join(parts_dir, f"{declaring_part}.py")
        for declaring_part, zone_name, _path in zones
    }
    stale_zones = stale_ids(manifest.get("keep_out_zones", {}), zone_to_script)
    return stale_unions, stale_zones, None


def _check_zone(
    declaring_part: str,
    zone_name: str,
    zone_path: str,
    all_unions: list[tuple[str | None, str]],
    stale_unions: set[str],
    stale_zones: set[str],
    stl_dir: str,
    trimesh: Any,
    check_interference: Callable[..., set[str]],
) -> list[dict]:
    """Check one declared zone against every foreign union. Returns the issues produced."""
    issues: list[dict] = []
    zone_key = f"{declaring_part}::{zone_name}"
    if zone_key in stale_zones:
        issues.append(
            make_issue(
                "geometry",
                "error",
                "stale_artifact",
                f"Keep-out zone '{zone_name}' (part '{declaring_part}'): exported STL "
                "is stale -- its source script changed since the model was last "
                "exported.",
                "Re-run the model export so this zone's STL reflects the current "
                "script, then re-run the quality gate.",
                zone_part=declaring_part,
                zone_name=zone_name,
            )
        )
        return issues

    fixed = [
        (pid, uid) for pid, uid in all_unions if pid != declaring_part and uid not in stale_unions
    ]
    for pid, uid in all_unions:
        if pid != declaring_part and uid in stale_unions:
            issues.append(
                make_issue(
                    "geometry",
                    "error",
                    "stale_artifact",
                    f"Union '{uid}': exported STL is stale -- its source script "
                    f"changed since the model was last exported (checked against "
                    f"keep-out zone '{zone_name}' declared by part '{declaring_part}').",
                    "Re-run the model export so this union's STL reflects the current "
                    "script, then re-run the quality gate.",
                    zone_part=declaring_part,
                    zone_name=zone_name,
                    union=uid,
                )
            )
    missing = [uid for _pid, uid in fixed if not os.path.exists(stl_path(stl_dir, uid))]
    if missing:
        issues.append(
            make_issue(
                "geometry",
                "warning",
                "check_skipped",
                f"Keep-out zone '{zone_name}' (part '{declaring_part}'): assembled union "
                f"STL not found ({', '.join(missing)})",
                "Run the model export so each union has an assembled STL.",
                zone_part=declaring_part,
                zone_name=zone_name,
            )
        )
        return issues

    zone_mesh = trimesh.load(zone_path, force="mesh")
    others = [(uid, trimesh.load(stl_path(stl_dir, uid), force="mesh")) for _pid, uid in fixed]

    names = check_interference(zone_mesh, others, penetration_tol_mm3=None)
    for uid in sorted(names):
        issues.append(
            make_issue(
                "geometry",
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


def run_keep_out_check(plan: dict, stl_dir: str, *, parts_dir: str | None = None) -> list[dict]:
    """Check every declared keep-out zone against every foreign union. Returns issues.

    Returns an empty list without loading the geometry stack when the model declares no
    keep-out zones (regardless of whether the collision backend is available). When
    `parts_dir` is given and an export manifest is present, a stale zone (its declaring
    part's script changed) or a stale foreign union is flagged as `stale_artifact` and
    excluded from that zone's intersection check.
    """
    zones = _discover_zones(plan, stl_dir)
    if not zones:
        return []

    # Geometry backend is optional, matching the kinematic/plate-clearance checks' degrade path.
    trimesh, check_interference, backend_issue = _load_geometry_backend()
    if backend_issue:
        return [backend_issue]
    assert check_interference is not None

    all_unions = [(part.get("id"), uid) for part, uid, _plate in iter_unions(plan)]

    issues: list[dict] = []

    stale_unions, stale_zones, staleness_issue = _compute_staleness(
        all_unions, zones, stl_dir, parts_dir
    )
    if staleness_issue:
        issues.append(staleness_issue)

    for declaring_part, zone_name, zone_path in zones:
        issues.extend(
            _check_zone(
                declaring_part,
                zone_name,
                zone_path,
                all_unions,
                stale_unions,
                stale_zones,
                stl_dir,
                trimesh,
                check_interference,
            )
        )

    return issues


def main() -> None:
    run_stl_dir_check_cli(
        "Keep-out-zone validation",
        "Directory holding exported <union_id>.stl and keep_out__*.stl files",
        run_keep_out_check,
    )


if __name__ == "__main__":
    main()
