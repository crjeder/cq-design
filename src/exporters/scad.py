"""SCAD exporter — mesh-based fallback.

NOTE: This output is NOT parametric. The .scad file contains an import()
of a companion STL. It cannot be edited as CadQuery source in OpenSCAD.
The CadQuery .py script is the parametric source of truth.
"""

import os

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Write a .scad file that imports a companion STL mesh.

    Produces two files:
      <path>          — the .scad wrapper (e.g. model.scad)
      <path stem>.stl — the companion mesh imported by the .scad

    The STL is placed next to the .scad file.
    """
    stem = os.path.splitext(path)[0]
    stl_path = stem + ".stl"
    stl_name = os.path.basename(stl_path)

    cq.exporters.export(result, stl_path, tolerance=0.01, angularTolerance=0.1)

    scad_content = (
        "// NOTE: This file is mesh-based (not parametric).\n"
        "// The CadQuery .py source is the parametric model.\n"
        "// Edit the .py script and re-export to update this file.\n"
        f'import("{stl_name}");\n'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(scad_content)
