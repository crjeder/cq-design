#!/usr/bin/env python3
"""Regenerate all build plates with each object in its print orientation.

This script is a deliverable: the cq-design skill copies it into the `build/`
directory of your working directory, alongside the per-part scripts and the bundled
build tooling (`exporters/`, `blocks/`, `model_export.py`, `print_orientation.py`,
`mesh_io.py`, `placement.py`). The working directory is a self-contained uv project,
so everything needed to rebuild the model lives here -- the skill does not have to be
installed.

How to re-generate the 3MF / STL files
---------------------------------------
The working directory is a uv project (it has its own `pyproject.toml`,
`.python-version`, and committed `uv.lock`). Sync the environment once, then run the
build with uv from the working-directory root:

    uv sync
    uv run python build/build.py

`uv sync` downloads a compatible Python (3.10-3.12) and installs the pinned
dependencies (CadQuery, trimesh, ...). Subsequent runs reuse the synced `.venv`.

Override the defaults when your layout differs:

    uv run python build/build.py --plan BUILD_PLAN.json --parts-dir build --out build

Arguments (all optional):
    --plan          BUILD_PLAN.json (default: the parent of build/)
    --parts-dir     directory of <part-id>.py scripts (default: this script's dir)
    --out           where the files are written (default: this script's dir)
    --orientations  accepted orientations JSON (default: orientations.json in --parts-dir)

Outputs written to --out:
    model.3mf            one named object per union, with plate metadata
    <union-id>.stl       one assembled-pose STL per union
    plate_<n>.stl        one fused STL per multi-union plate

When `orientations.json` (the skill's accepted per-union orientations) sits next to
the part scripts, build.py reuses it so the plates match what the skill delivered;
otherwise it computes each orientation fresh with the same `print_orientation` tooling,
honoring the plan's `optimize_for` mode (per-part override, else plan-level, else
`strength`). Either way the deliverables are written via `model_export`, exactly as the
skill writes them.

The bundled tooling sits in this script's own directory, which Python places on
`sys.path` automatically when you run `python build/build.py`, so the imports below
resolve without any path manipulation.
"""

import argparse
import json
import os
import sys
import tempfile

import cadquery as cq

from exporters import _load_result
from mesh_io import load_mesh
from model_export import export_model
from print_orientation import optimize_orientation
from units import resolve_unions


def _orientation_for(
    result: cq.Workplane, part: dict, overhang_deg: float, optimize_for: str
) -> dict:
    """Recommended print orientation for one union's authored geometry.

    `optimize_orientation` scores a mesh in its authored frame, so the result is
    exported to a throwaway STL and reloaded. Uses the part's declared `load.dir` /
    `show_face.dir` when present (the optimizer infers them otherwise) and the
    effective `optimize_for` mode resolved from the plan.
    """
    load = part.get("load")
    load_dir = load["dir"] if load else None
    show_face = part.get("show_face")
    show_dir = show_face["dir"] if show_face else None
    with tempfile.TemporaryDirectory() as tmp:
        stl = os.path.join(tmp, "authored.stl")
        cq.exporters.export(result, stl)
        mesh = load_mesh(stl)
    return optimize_orientation(
        mesh, overhang_deg, load_dir, optimize_for=optimize_for, show_face=show_dir
    )


def resolve_orientations(
    plan: dict, parts_dir: str, orientations_path: str
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Return ({part_id: {"rotate": [...]}}, {part_id: full orientation result}).

    Reuses the skill's accepted `orientations.json` when it exists (so the plates
    match the delivered ones); otherwise computes each union's orientation fresh.
    Raises RuntimeError naming the union when a part script cannot be loaded or
    oriented, so the caller can fail fast with an actionable message.
    """
    accepted: dict[str, dict] = {}
    if os.path.isfile(orientations_path):
        with open(orientations_path, encoding="utf-8") as f:
            accepted = json.load(f)

    overhang_deg = plan["constraints"]["overhang_max_deg"]
    plan_mode = plan.get("optimize_for", "strength")
    orientations: dict[str, dict] = {}
    summary: dict[str, dict] = {}
    for part in plan.get("parts", []):
        pid = part["id"]
        script = os.path.join(parts_dir, f"{pid}.py")
        optimize_for = part.get("optimize_for", plan_mode)
        union_ids = [u["id"] for u in part.get("unions", [])] or [pid]
        wp_by_uid: dict[str, cq.Workplane] | None = None  # loaded lazily, once per part
        for uid in union_ids:
            if uid in accepted:
                chosen = accepted[uid]
            else:
                try:
                    if wp_by_uid is None:
                        wp_by_uid = dict(resolve_unions(part, _load_result(script)))
                    chosen = _orientation_for(wp_by_uid[uid], part, overhang_deg, optimize_for)
                except Exception as exc:
                    raise RuntimeError(f"union {uid!r}: {exc}") from exc
            orientations[uid] = {"rotate": chosen["rotate"]}
            summary[uid] = chosen
    return orientations, summary


def _print_summary(summary: dict[str, dict], result: dict) -> None:
    """Print the chosen orientation and output path for each union, then plates."""
    for pid, chosen in summary.items():
        rot = ", ".join(f"{s['axis']}{s['angle_deg']:+g}" for s in chosen["rotate"])
        path = result["union_stls"].get(pid, "?")
        print(f"{pid}: orientation [{rot}] -> {path}")
    print(f"model.3mf: {result['model_3mf']}")
    for plate, plate_path in result["plate_stls"].items():
        print(f"plate {plate}: {plate_path}")


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Regenerate build plates with objects in print orientation"
    )
    parser.add_argument(
        "--plan",
        default=os.path.join(script_dir, os.pardir, "BUILD_PLAN.json"),
        help="Path to BUILD_PLAN.json (default: alongside the build dir)",
    )
    parser.add_argument(
        "--parts-dir",
        default=script_dir,
        help="Directory of <id>.py part scripts (default: this script's dir)",
    )
    parser.add_argument(
        "--out",
        default=script_dir,
        help="Output directory for the plates (default: this script's dir)",
    )
    parser.add_argument(
        "--orientations",
        default=None,
        help="Accepted orientations JSON (default: orientations.json in --parts-dir)",
    )
    args = parser.parse_args()

    orientations_path = args.orientations or os.path.join(args.parts_dir, "orientations.json")

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    try:
        orientations, summary = resolve_orientations(plan, args.parts_dir, orientations_path)
        result = export_model(plan, args.parts_dir, args.out, orientations)
    except Exception as exc:
        sys.stderr.write(f"build failed: {exc}\n")
        sys.exit(1)

    _print_summary(summary, result)
    sys.exit(0)


if __name__ == "__main__":
    main()
