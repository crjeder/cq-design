"""STL exporter — native CadQuery/OCC tessellation."""

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to STL with consistent tessellation settings."""
    cq.exporters.export(result, path, tolerance=0.01, angularTolerance=0.1)
