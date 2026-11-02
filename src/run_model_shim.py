"""
Shim: execute a CadQuery model script and auto-export the `result` variable.

Called by run_cadquery_model.py as:
    python run_model_shim.py path/to/model.py

The wrapper sets cwd to a private temp dir before invoking this shim, so the
exported STL lands there where the wrapper can find it.
"""

import glob
import json
import os
import runpy
import sys

from units import KEEP_OUT_KEY


def main() -> None:
    script_path = sys.argv[1]

    # Run the model script.  runpy sets __file__ correctly so relative paths
    # inside the script (e.g. reading a companion CSV) resolve as expected.
    ns = runpy.run_path(script_path, init_globals={"__file__": script_path})

    result = ns.get("result")
    if result is None:
        # Script exports its own files or has no geometry -- nothing to do.
        return

    stem = os.path.splitext(os.path.basename(script_path))[0]
    bodies = (
        {uid: wp for uid, wp in result.items() if uid != KEEP_OUT_KEY}
        if isinstance(result, dict)
        else {stem: result}
    )
    # BRepCheck every body; the wrapper turns non-empty lists into invalid_brep errors.
    from blocks.imported import brep_statuses

    checks = {}
    for uid, wp in bodies.items():
        shape = wp.val() if hasattr(wp, "val") else wp
        checks[uid] = brep_statuses(shape.wrapped)
    with open("brep_check.json", "w", encoding="utf-8") as f:
        json.dump(checks, f)

    # --deliver without --print-rotate: write the delivery formats from this load instead of
    # having the wrapper import the script a second time. The wrapper reads the manifest.
    # An invalid body is never delivered.
    deliver_manifest = os.environ.get("CQ_DELIVER_MANIFEST")
    if deliver_manifest and not any(checks.values()):
        from exporters import export_loaded

        manifest: dict[str, object]
        try:
            paths = export_loaded(
                result,
                stem,
                os.environ["CQ_DELIVER_FORMATS"].split(","),
                os.environ["CQ_DELIVER_DIR"],
            )
            manifest = {"paths": paths}
        except Exception as exc:
            manifest = {"error": str(exc)}
        with open(deliver_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f)

    # Skip auto-export if the script already wrote an STL itself.
    if glob.glob("*.stl") or glob.glob("*.STL"):
        return

    import cadquery as cq

    # A multi-union part sets `result` to a dict {union_id: Workplane}; export one STL per
    # union so the wrapper validates each body. A plain Workplane keeps the script-stem name.
    # The reserved `keep_out` key (declared keep-out zones) is never a union and is skipped
    # here -- it is validated by the whole-model keep-out check, not the per-part wrapper.
    if isinstance(result, dict):
        for uid, wp in result.items():
            if uid == KEEP_OUT_KEY:
                continue
            cq.exporters.export(wp, f"{uid}.stl")
    else:
        cq.exporters.export(result, f"{stem}.stl")


if __name__ == "__main__":
    main()
