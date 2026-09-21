#!/usr/bin/env python3
"""Regenerate all build plates with each object in its print orientation.

This script is a deliverable: the cq-design skill copies it into the `build/`
directory of your working directory, alongside the per-part scripts. The bundled
build tooling (`exporters/`, `blocks/`, `model_export.py`, `print_orientation.py`,
`mesh_io.py`, `placement.py`, `mate_chain.py`) lives in a sibling `lib/` directory,
not build/ itself -- build/ holds only the part scripts you actually edit. The
working directory is a self-contained uv project, so everything needed to rebuild
the model lives here -- the skill does not have to be installed.

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

    uv run python build/build.py --plan BUILD_PLAN.json --parts-dir build --out . --stl-out stl

Arguments (all optional):
    --plan          BUILD_PLAN.json (default: the parent of build/, i.e. the project root)
    --parts-dir     directory of <part-id>.py scripts (default: this script's dir)
    --out           where model.3mf is written (default: the project root)
    --stl-out       where the STLs are written (default: <project root>/stl)
    --orientations  accepted orientations JSON (default: orientations.json in --parts-dir)

Outputs:
    model.3mf (in --out)         one named object per union, with plate metadata
    <union-id>.stl (in --stl-out)  one assembled-pose STL per union
    plate_<n>.stl (in --stl-out)   one fused STL per multi-union plate

When `orientations.json` (the skill's accepted per-union orientations) sits next to
the part scripts, build.py reuses it so the plates match what the skill delivered;
otherwise it computes each orientation fresh with the same `print_orientation` tooling,
honoring the plan's `optimize_for` mode (per-part override, else plan-level, else
`strength`). Either way the deliverables are written via `model_export`, exactly as the
skill writes them.

The bundled tooling sits in a `lib/` directory next to this script's own directory
(i.e. `../lib` relative to build.py), so it is added to `sys.path` explicitly below
before the imports that depend on it.
"""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "lib"))

import cadquery as cq

from exporters import _load_result
from freshness import is_stale, script_hash
from mesh_io import load_mesh
from model_export import export_model
from print_orientation import optimize_orientation
from units import load_plan, resolve_unions


def _orientation_for(
    result: cq.Workplane,
    part: dict,
    overhang_deg: float,
    optimize_for: str,
    bridge_max_mm: float = 10.0,
) -> dict:
    """Recommended print orientation for one union's authored geometry.

    `optimize_orientation` scores a mesh in its authored frame, so the result is
    exported to a throwaway STL and reloaded. Uses the part's declared `load.dir` /
    `load.type` / `show_face.dir` when present (the optimizer infers direction
    otherwise and defaults type to `tension`) and the effective `optimize_for` mode
    resolved from the plan.
    """
    load = part.get("load")
    load_dir = load["dir"] if load else None
    load_type = load.get("type", "tension") if load else "tension"
    show_face = part.get("show_face")
    show_dir = show_face["dir"] if show_face else None
    with tempfile.TemporaryDirectory() as tmp:
        stl = os.path.join(tmp, "authored.stl")
        cq.exporters.export(result, stl)
        mesh = load_mesh(stl)
    return optimize_orientation(
        mesh,
        overhang_deg,
        load_dir,
        optimize_for=optimize_for,
        show_face=show_dir,
        load_type=load_type,
        bridge_max_mm=bridge_max_mm,
    )


def resolve_orientations(
    plan: dict, parts_dir: str, orientations_path: str
) -> tuple[dict[str, dict], dict[str, dict], list[str]]:
    """Return ({part_id: {"rotate": [...]}}, {part_id: full orientation result}, recomputed).

    Reuses the skill's accepted `orientations.json` when it exists (so the plates
    match the delivered ones); otherwise computes each union's orientation fresh. An
    accepted entry is checked against its union's current source script via its
    `source_script_hash` stamp: a mismatch means the part script changed since the
    entry was accepted, so it is recomputed instead of reused (and the fresh result is
    stamped); an entry with no stamp is reused unconditionally, matching the behavior
    before provenance stamping existed. `recomputed` lists the union ids that were
    recomputed specifically because their accepted entry was stale.
    Raises RuntimeError naming the union when a part script cannot be loaded or
    oriented, so the caller can fail fast with an actionable message.
    """
    accepted: dict[str, dict] = {}
    if os.path.isfile(orientations_path):
        with open(orientations_path, encoding="utf-8") as f:
            accepted = json.load(f)

    overhang_deg = plan["constraints"]["overhang_max_deg"]
    bridge_max_mm = plan["constraints"].get("bridge_max_mm", 10.0)
    plan_mode = plan.get("optimize_for", "strength")
    orientations: dict[str, dict] = {}
    summary: dict[str, dict] = {}
    recomputed: list[str] = []
    for part in plan.get("parts", []):
        pid = part["id"]
        script = os.path.join(parts_dir, f"{pid}.py")
        optimize_for = part.get("optimize_for", plan_mode)
        union_ids = [u["id"] for u in part.get("unions", [])] or [pid]
        wp_by_uid: dict[str, cq.Workplane] | None = None  # loaded lazily, once per part
        for uid in union_ids:
            entry = accepted.get(uid)
            stale = entry is not None and is_stale(entry.get("source_script_hash"), script)
            if entry is not None and not stale:
                chosen = entry
            else:
                try:
                    if wp_by_uid is None:
                        wp_by_uid = dict(resolve_unions(part, _load_result(script)))
                    chosen = _orientation_for(
                        wp_by_uid[uid], part, overhang_deg, optimize_for, bridge_max_mm
                    )
                except Exception as exc:
                    raise RuntimeError(f"union {uid!r}: {exc}") from exc
                chosen = {**chosen, "source_script_hash": script_hash(script)}
                if stale:
                    recomputed.append(uid)
            orientations[uid] = {"rotate": chosen["rotate"]}
            summary[uid] = chosen
    return orientations, summary, recomputed


def _print_summary(summary: dict[str, dict], result: dict, recomputed: list[str]) -> None:
    """Print the chosen orientation and output path for each union, then plates."""
    for pid, chosen in summary.items():
        rot = ", ".join(f"{s['axis']}{s['angle_deg']:+g}" for s in chosen["rotate"])
        path = result["union_stls"].get(pid, "?")
        print(f"{pid}: orientation [{rot}] -> {path}")
    print(f"model.3mf: {result['model_3mf']}")
    for plate, plate_path in result["plate_stls"].items():
        print(f"plate {plate}: {plate_path}")
    if recomputed:
        print(f"recomputed (source script changed since accepted): {', '.join(recomputed)}")


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, os.pardir)
    parser = argparse.ArgumentParser(
        description="Regenerate build plates with objects in print orientation"
    )
    parser.add_argument(
        "--plan",
        default=os.path.join(project_root, "BUILD_PLAN.json"),
        help="Path to BUILD_PLAN.json (default: the project root)",
    )
    parser.add_argument(
        "--parts-dir",
        default=script_dir,
        help="Directory of <id>.py part scripts (default: this script's dir)",
    )
    parser.add_argument(
        "--out",
        default=project_root,
        help="Output directory for model.3mf (default: the project root)",
    )
    parser.add_argument(
        "--stl-out",
        default=os.path.join(project_root, "stl"),
        help="Output directory for the STLs (default: <project root>/stl)",
    )
    parser.add_argument(
        "--orientations",
        default=None,
        help="Accepted orientations JSON (default: orientations.json in --parts-dir)",
    )
    args = parser.parse_args()

    orientations_path = args.orientations or os.path.join(args.parts_dir, "orientations.json")

    plan = load_plan(args.plan)

    try:
        orientations, summary, recomputed = resolve_orientations(
            plan, args.parts_dir, orientations_path
        )
        result = export_model(plan, args.parts_dir, args.out, orientations, stl_dir=args.stl_out)
    except Exception as exc:
        sys.stderr.write(f"build failed: {exc}\n")
        sys.exit(1)

    _print_summary(summary, result, recomputed)
    sys.exit(0)


if __name__ == "__main__":
    main()
