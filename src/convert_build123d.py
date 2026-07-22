"""build123d -> CadQuery conversion aid (Phase 0 rung 1).

Both libraries wrap OpenCASCADE, so a build123d script converts mostly by renaming
imports and API calls, not by re-deriving geometry. This module is notes, not a
transpiler: `API_MAPPING` documents the known correspondences the LLM applies by hand
while re-authoring the script, and `smoke_check` runs the converted CadQuery script
through the existing wrapper (`run_cadquery_model.py`) to report the same JSON verdict
any generated part script gets.

Usage:
    python convert_build123d.py --mapping
    python convert_build123d.py --smoke-check converted_part.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import TypedDict


class MappingEntry(TypedDict):
    b123d: str
    cadquery: str
    notes: str | None


# Known build123d -> CadQuery correspondences. Not exhaustive or executable -- a
# reference table for the LLM performing the conversion by hand. `b123d` is the
# build123d symbol/pattern, `cadquery` is its CadQuery equivalent, `notes` calls out
# behavioral differences that a blind rename would miss.
API_MAPPING: list[MappingEntry] = [
    {
        "b123d": "from build123d import *",
        "cadquery": "import cadquery as cq",
        "notes": "CadQuery has no builder-context globals; every op is a Workplane method call.",
    },
    {
        "b123d": "with BuildPart() as p: ...",
        "cadquery": "result = cq.Workplane('XY')...",
        "notes": "Builder-context (BuildPart/BuildSketch/BuildLine) has no CadQuery "
        "equivalent -- flatten to a fluent Workplane chain.",
    },
    {
        "b123d": "Box(x, y, z)",
        "cadquery": "cq.Workplane('XY').box(x, y, z)",
        "notes": "build123d Box is centered on all axes by default like CadQuery's box().",
    },
    {
        "b123d": "Cylinder(radius, height)",
        "cadquery": "cq.Workplane('XY').circle(radius).extrude(height)",
        "notes": None,
    },
    {
        "b123d": "extrude(sketch, amount)",
        "cadquery": ".extrude(amount)",
        "notes": "build123d extrude is a free function taking a sketch; CadQuery extrudes "
        "the current Workplane's 2D profile.",
    },
    {
        "b123d": "fillet(objects, radius)",
        "cadquery": ".edges(<selector>).fillet(radius)",
        "notes": "build123d selects edges by object reference; CadQuery selects via a "
        "string selector (e.g. '|Z', '>Z') on the current solid.",
    },
    {
        "b123d": "chamfer(objects, length)",
        "cadquery": ".edges(<selector>).chamfer(length)",
        "notes": "Same selector-string translation as fillet.",
    },
    {
        "b123d": "Pos(x, y, z) / Rot(x, y, z)",
        "cadquery": ".translate((x, y, z)) / .rotate(axis, angle)",
        "notes": "build123d locations compose x/y/z position and rotation in one object; "
        "split into CadQuery's separate translate/rotate calls.",
    },
    {
        "b123d": "add(other) / subtract(other)",
        "cadquery": ".union(other) / .cut(other)",
        "notes": None,
    },
    {
        "b123d": "GridLocations(x_spacing, y_spacing, x_count, y_count)",
        "cadquery": ".rarray(x_spacing, y_spacing, x_count, y_count)",
        "notes": None,
    },
    {
        "b123d": "PolarLocations(radius, count)",
        "cadquery": ".polarArray(radius, 0, 360, count)",
        "notes": "Check start/stop angle convention -- build123d's default sweep and "
        "CadQuery's may differ.",
    },
]


def smoke_check(script_path: str, skill_root: str | None = None, timeout: int = 180) -> dict:
    """Run a converted CadQuery script through run_cadquery_model.py and return its JSON verdict.

    `skill_root` defaults to the directory containing this file (src/).
    """
    if skill_root is None:
        skill_root = os.path.dirname(os.path.abspath(__file__))
    wrapper = os.path.join(skill_root, "run_cadquery_model.py")
    proc = subprocess.run(
        [sys.executable, wrapper, os.path.abspath(script_path), "--strict"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "errors": [
                {
                    "type": "smoke_check_failed",
                    "message": "wrapper produced no parseable JSON",
                    "hint": proc.stderr.strip() or "no stderr captured",
                }
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapping", action="store_true", help="print the build123d->CadQuery mapping table as JSON"
    )
    parser.add_argument(
        "--smoke-check",
        metavar="SCRIPT",
        help="run a converted CadQuery script through the wrapper",
    )
    args = parser.parse_args(argv)

    if args.mapping:
        print(json.dumps(API_MAPPING, indent=2))
        return 0

    if args.smoke_check:
        report = smoke_check(args.smoke_check)
        print(json.dumps(report, indent=2))
        return 0 if report.get("success") else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
