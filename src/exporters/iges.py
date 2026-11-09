"""IGES exporter — legacy CAD exchange format via OCP IGESControl."""

import cadquery as cq


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to IGES format."""
    from OCP.IGESControl import IGESControl_Writer  # type: ignore[import-not-found]

    writer = IGESControl_Writer()
    shapes = [v for v in result.vals() if isinstance(v, cq.Shape)]
    shape = shapes[0] if len(shapes) == 1 else cq.Compound.makeCompound(shapes)
    writer.AddShape(shape.wrapped)
    writer.Write(path)
