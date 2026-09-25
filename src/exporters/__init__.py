"""Modular exporter: derive all output formats from the CadQuery result object.

Usage:
    from exporters import run_exporters
    paths = run_exporters("model.py", ["stl", "3mf", "step"], "/output/dir")

Adding a new format:
    1. Create exporters/<format>.py with export(result, path) -> None
    2. Import it below and add it to _REGISTRY
    No other files need modification.
"""

import importlib.util
import json
import os
import sys

# importlib.util is used only in _load_result (spec_from_file_location)
import cadquery as cq

from exporters import iges as _iges_mod
from exporters import obj as _obj_mod
from exporters import scad as _scad_mod
from exporters import step as _step_mod
from exporters import stl as _stl_mod
from exporters import threemf as _threemf_mod

# Map format key → (exporter_module, file_extension)
# All values are statically imported above — no dynamic module loading.
_REGISTRY: dict[str, tuple] = {
    "stl": (_stl_mod, ".stl"),
    "step": (_step_mod, ".step"),
    "3mf": (_threemf_mod, ".3mf"),
    "obj": (_obj_mod, ".obj"),
    "iges": (_iges_mod, ".iges"),
    "scad": (_scad_mod, ".scad"),
}


class ExportError(Exception):
    pass


def _load_result(
    script_path: str, print_rotate: list | None = None
) -> "cq.Workplane | dict[str, cq.Workplane]":
    """Import a model script and return its top-level `result` variable.

    `result` is a `cq.Workplane` (one union) or a `dict[str, cq.Workplane]` mapping union id
    to geometry (a multi-union part); callers normalize via `units.resolve_unions`.

    `print_rotate` (an orientation's `rotate` list) is exposed to the script as
    `CQ_PRINT_ROTATE` for the duration of the load, so `blocks.print_up()` resolves the
    accepted print pose; None leaves the authoring default (+Z).
    """
    script_path = os.path.abspath(script_path)
    script_dir = os.path.dirname(script_path)
    # __file__ is src/exporters/__init__.py; go up two levels to src/, not one -- a
    # part script's `from blocks import ...` needs src/ on the path, not src/exporters/.
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    inserted = [p for p in (script_dir, skill_root) if p not in sys.path]
    for path in inserted:
        sys.path.insert(0, path)

    # Run from the script's directory so relative exports resolve correctly
    old_cwd = os.getcwd()
    old_rotate = os.environ.get("CQ_PRINT_ROTATE")
    if print_rotate is not None:
        os.environ["CQ_PRINT_ROTATE"] = json.dumps(print_rotate)
    try:
        module_name = os.path.splitext(os.path.basename(script_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise ExportError(f"Cannot load script: {script_path}")

        module = importlib.util.module_from_spec(spec)
        os.chdir(script_dir)
        spec.loader.exec_module(module)

        if not hasattr(module, "result"):
            raise ExportError(
                f"Script '{script_path}' does not define a top-level 'result' variable. "
                "Add: result = <your_cq_workplane> before the export call."
            )
        return module.result
    finally:
        os.chdir(old_cwd)
        if print_rotate is not None:
            if old_rotate is None:
                os.environ.pop("CQ_PRINT_ROTATE", None)
            else:
                os.environ["CQ_PRINT_ROTATE"] = old_rotate
        for path in inserted:
            sys.path.remove(path)


def run_exporters(script_path: str, formats: list[str], output_dir: str) -> list[str]:
    """Export the model to all requested formats. Returns list of output paths.

    Args:
        script_path: absolute or relative path to the CadQuery .py model
        formats: list of format keys, e.g. ["stl", "3mf", "step"]
        output_dir: directory where output files are written

    Raises:
        ExportError: if the script cannot be loaded or a format is unknown
    """
    unknown = [f for f in formats if f not in _REGISTRY]
    if unknown:
        raise ExportError(f"Unknown export format(s): {unknown}. Supported: {sorted(_REGISTRY)}")

    os.makedirs(output_dir, exist_ok=True)
    cq_result = _load_result(script_path)

    from units import KEEP_OUT_KEY

    stem = os.path.splitext(os.path.basename(script_path))[0]
    produced = []

    # A multi-union part sets `result` to a dict {union_id: Workplane}; export one file
    # per union so each body is delivered separately (matching run_model_shim). A plain
    # Workplane keeps the script-stem name. The reserved keep-out key is never a union.
    if isinstance(cq_result, dict):
        targets = [(uid, wp) for uid, wp in cq_result.items() if uid != KEEP_OUT_KEY]
    else:
        targets = [(stem, cq_result)]

    for name, wp in targets:
        for fmt in formats:
            exporter_mod, ext = _REGISTRY[fmt]
            out_path = os.path.join(output_dir, name + ext)
            exporter_mod.export(wp, out_path)
            produced.append(out_path)

    return produced
