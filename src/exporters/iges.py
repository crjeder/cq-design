"""IGES exporter — legacy CAD exchange format via OCP IGESControl."""

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to IGES format."""
    from OCP.IGESControl import IGESControl_Writer  # type: ignore[import-not-found]

    writer = IGESControl_Writer()
    shape = result.val()
    writer.AddShape(shape.wrapped)  # type: ignore[union-attr]
    writer.Write(path)
