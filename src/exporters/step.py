"""STEP exporter — for CAD editing in Fusion 360, FreeCAD, etc."""

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to STEP format."""
    cq.exporters.export(result, path)
