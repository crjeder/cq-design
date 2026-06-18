"""3MF exporter for Bambu Studio / PrusaSlicer / OrcaSlicer.

Strategy: use cq.exporters.export() directly when available (preserves cavities),
falling back to trimesh for older CadQuery versions.

WARNING on the trimesh fallback: trimesh's 3MF writer can mangle internal
cavities (enclosed voids, magnet pockets). Prefer direct CadQuery export.
"""

import os
import tempfile

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to 3MF format."""
    # Try native CadQuery export first (preserves internal cavities)
    try:
        cq.exporters.export(result, path)
        return
    except Exception:
        pass

    # Fallback: STL -> trimesh -> 3MF (no cavity preservation)
    import trimesh

    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tf:
        tmp_stl = tf.name
    try:
        cq.exporters.export(result, tmp_stl, tolerance=0.01, angularTolerance=0.1)
        mesh = trimesh.load(tmp_stl, force="mesh")
        mesh.export(path)
    finally:
        if os.path.exists(tmp_stl):
            os.unlink(tmp_stl)
