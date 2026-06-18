"""
Shim: execute a CadQuery model script and auto-export the `result` variable.

Called by run_cadquery_model.py as:
    python run_model_shim.py path/to/model.py

The wrapper sets cwd to a private temp dir before invoking this shim, so the
exported STL lands there where the wrapper can find it.
"""

import glob
import os
import runpy
import sys


def main() -> None:
    script_path = sys.argv[1]

    # Run the model script.  runpy sets __file__ correctly so relative paths
    # inside the script (e.g. reading a companion CSV) resolve as expected.
    ns = runpy.run_path(script_path, init_globals={"__file__": script_path})

    result = ns.get("result")
    if result is None:
        # Script exports its own files or has no geometry -- nothing to do.
        return

    # Skip auto-export if the script already wrote an STL itself.
    if glob.glob("*.stl") or glob.glob("*.STL"):
        return

    import cadquery as cq

    stem = os.path.splitext(os.path.basename(script_path))[0]
    cq.exporters.export(result, f"{stem}.stl")


if __name__ == "__main__":
    main()
