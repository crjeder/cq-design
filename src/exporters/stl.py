"""STL exporter — native CadQuery/OCC tessellation."""

import cadquery as cq

import mesh_io


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to STL with consistent tessellation settings."""
    cq.exporters.export(
        result,
        path,
        tolerance=mesh_io.EXPORT_TESSELLATION_TOLERANCE_MM,
        angularTolerance=mesh_io.EXPORT_TESSELLATION_ANGULAR_TOLERANCE_DEG,
    )
