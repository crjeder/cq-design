#!/usr/bin/env python3
"""Regenerate all build plates with each object in its print orientation.

This script is a deliverable: the cq-design skill copies it into the `build/`
directory of your working directory (substituting the skill's `src/` path for the
`{{SKILL_SRC}}` placeholder below). Run it to rebuild `model.3mf` and the per-union
/ per-plate STLs after hand-editing a part script, without re-invoking the skill.

    python build/build.py
    python build/build.py --plan BUILD_PLAN.json --parts-dir build --out build

When `orientations.json` (the skill's accepted per-union orientations) sits next to
the part scripts, build.py reuses it so the plates match what the skill delivered;
otherwise it computes each orientation fresh (strength first, support second) with the
same `print_orientation` tooling. Either way the deliverables are written via
`model_export`, exactly as the skill writes them.
"""

import argparse
import os
import sys
import tempfile

# Substituted by the skill at copy time with the absolute path to its src/ dir.
SKILL_SRC = "{{SKILL_SRC}}"


def _bootstrap() -> None:
    """Put the skill's src/ on sys.path so the shared tooling and blocks import."""
    if not os.path.isdir(SKILL_SRC):
        sys.stderr.write(
            f"cq-design skill src not found at {SKILL_SRC!r}: the skill that wrote "
            "this build.py was moved or uninstalled. Re-run the skill to refresh "
            "build.py, or repair SKILL_SRC to point at the skill's src/ directory.\n"
        )
        sys.exit(2)
    if SKILL_SRC not in sys.path:
        sys.path.insert(0, SKILL_SRC)


_bootstrap()

import json  # noqa: E402  (must follow sys.path bootstrap)

import cadquery as cq  # noqa: E402

from exporters import _load_result  # noqa: E402
from mesh_io import load_mesh  # noqa: E402
from model_export import export_model  # noqa: E402
from print_orientation import optimize_orientation  # noqa: E402


def _orientation_for(result: cq.Workplane, part: dict, overhang_deg: float) -> dict:
    """Recommended print orientation for one union's authored geometry.

    `optimize_orientation` scores a mesh in its authored frame, so the result is
    exported to a throwaway STL and reloaded. Uses the part's declared `load.dir`
    when present; the optimizer infers a load axis otherwise.
    """
    load = part.get("load")
    load_dir = load["dir"] if load else None
    with tempfile.TemporaryDirectory() as tmp:
        stl = os.path.join(tmp, "authored.stl")
        cq.exporters.export(result, stl)
        mesh = load_mesh(stl)
    return optimize_orientation(mesh, overhang_deg, load_dir)


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
    orientations: dict[str, dict] = {}
    summary: dict[str, dict] = {}
    for part in plan.get("parts", []):
        pid = part["id"]
        if pid in accepted:
            chosen = accepted[pid]
        else:
            script = os.path.join(parts_dir, f"{pid}.py")
            try:
                result = _load_result(script)
                chosen = _orientation_for(result, part, overhang_deg)
            except Exception as exc:
                raise RuntimeError(f"union {pid!r}: {exc}") from exc
        orientations[pid] = {"rotate": chosen["rotate"]}
        summary[pid] = chosen
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

    orientations_path = args.orientations or os.path.join(
        args.parts_dir, "orientations.json"
    )

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    try:
        orientations, summary = resolve_orientations(
            plan, args.parts_dir, orientations_path
        )
        result = export_model(plan, args.parts_dir, args.out, orientations)
    except Exception as exc:
        sys.stderr.write(f"build failed: {exc}\n")
        sys.exit(1)

    _print_summary(summary, result)
    sys.exit(0)


if __name__ == "__main__":
    main()
