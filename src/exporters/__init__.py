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
import os
import sys
# importlib.util is used only in _load_result (spec_from_file_location)

import cadquery as cq

from exporters import stl as _stl_mod
from exporters import step as _step_mod
from exporters import threemf as _threemf_mod
from exporters import obj as _obj_mod
from exporters import iges as _iges_mod
from exporters import scad as _scad_mod

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


def _load_result(script_path: str) -> cq.Workplane:
    """Import a model script and return its top-level `result` variable."""
    script_path = os.path.abspath(script_path)
    script_dir = os.path.dirname(script_path)
    skill_root = os.path.dirname(os.path.abspath(__file__))

    for path in (script_dir, skill_root):
        if path not in sys.path:
            sys.path.insert(0, path)

    module_name = os.path.splitext(os.path.basename(script_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ExportError(f"Cannot load script: {script_path}")

    module = importlib.util.module_from_spec(spec)
    # Run from the script's directory so relative exports resolve correctly
    old_cwd = os.getcwd()
    try:
        os.chdir(script_dir)
        spec.loader.exec_module(module)
    finally:
        os.chdir(old_cwd)

    if not hasattr(module, "result"):
        raise ExportError(
            f"Script '{script_path}' does not define a top-level 'result' variable. "
            "Add: result = <your_cq_workplane> before the export call."
        )
    return module.result


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
        raise ExportError(
            f"Unknown export format(s): {unknown}. Supported: {sorted(_REGISTRY)}"
        )

    os.makedirs(output_dir, exist_ok=True)
    cq_result = _load_result(script_path)

    stem = os.path.splitext(os.path.basename(script_path))[0]
    produced = []

    for fmt in formats:
        exporter_mod, ext = _REGISTRY[fmt]
        out_path = os.path.join(output_dir, stem + ext)
        exporter_mod.export(cq_result, out_path)
        produced.append(out_path)

    return produced
