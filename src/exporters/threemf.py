"""3MF exporter for Bambu Studio / PrusaSlicer / OrcaSlicer.

Tessellates the shape and welds coincident vertices before writing (via
exporters.threemf_multi.write_single_3mf). CadQuery's native ThreeMFWriter emits
the raw per-face tessellation without welding shared face seams, which slicers
report as thousands of non-manifold edges even though the geometry is sound; the
welded path avoids that. Internal cavities are preserved because tessellation
includes inner-wall faces.
"""

import cadquery as cq

from exporters.threemf_multi import write_single_3mf


def export(result: cq.Workplane, path: str) -> None:
    """Export CadQuery result to 3MF format with welded (manifold) vertices."""
    shape = cq.Compound.makeCompound(result.vals())  # type: ignore[arg-type]  # vals() are Shapes here
    write_single_3mf(shape, path)
