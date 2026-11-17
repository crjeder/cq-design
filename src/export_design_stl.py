#!/usr/bin/env python3
"""Run a project build script and write its designed-pose STL + feature record.

Usage:
    python3 export_design_stl.py build/holder.py [preview/design.stl]

Writes the STL (tolerance 0.05 mm, angular 0.1 rad, build pose, never delivered) and
`<out stem>.features.json` beside it: one record per stage label passed to
`cq_verify.verify_boolean` / `verify_stage` during the run. Prints one JSON object
`{success, stl, features, errors}`; exit 0 on success, 1 on failure.
"""

import contextlib
import io
import json
import os
import sys

import cadquery as cq

import cq_verify
import preview
from freshness import script_hash
from render_preview import _load_script_result

TOLERANCE_MM = 0.05
ANGULAR_TOLERANCE = 0.1


def export_design_stl(script: str, out_stl: str) -> dict:
    """Run `script`, write `out_stl` and its features file; return the JSON contract."""
    errors, features_path = [], os.path.splitext(out_stl)[0] + ".features.json"
    skill_root = os.path.dirname(os.path.abspath(__file__))
    cq_verify.start_stage_recording()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            result = _load_script_result(os.path.abspath(script), skill_root)
    except SystemExit:
        errors.append({"type": "script_error", "message": stderr.getvalue().strip(), "hint": ""})
        result = None
    features = cq_verify.stop_stage_recording()
    if result is not None:
        os.makedirs(os.path.dirname(os.path.abspath(out_stl)), exist_ok=True)
        shape = preview._get_shape(result)
        cq.exporters.export(
            cq.Workplane().add(shape),
            out_stl,
            tolerance=TOLERANCE_MM,
            angularTolerance=ANGULAR_TOLERANCE,
        )
        with open(features_path, "w") as f:
            json.dump(
                {"features": features, "source_script_hash": script_hash(script)}, f, indent=2
            )
    return {
        "success": not errors,
        "stl": None if errors else out_stl,
        "features": None if errors else features_path,
        "errors": errors,
    }


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("usage: export_design_stl.py <build_script> [out.stl]", file=sys.stderr)
        sys.exit(2)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("preview", "design.stl")
    report = export_design_stl(sys.argv[1], out)
    print(json.dumps(report))
    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
