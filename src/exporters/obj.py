"""OBJ exporter via trimesh in-memory conversion."""

import os
import tempfile

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to OBJ format via trimesh."""
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
