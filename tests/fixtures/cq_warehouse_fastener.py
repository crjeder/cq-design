"""Fixture: CadQuery script that uses cq_warehouse fasteners."""

import cadquery as cq
from cadquery import Solid
from cq_warehouse.fastener import HexHeadScrew, HexNut  # type: ignore[import-untyped]

bolt = HexHeadScrew(size="M6-1", length=20, fastener_type="iso4014", simple=True)
nut = HexNut(size="M6-1", fastener_type="iso4033", simple=True)

# Cast to plain Solid before any CadQuery transform — cq_warehouse subclasses
# have __init__ signatures incompatible with CadQuery's internal copy mechanism.
bolt_solid = Solid(bolt.wrapped)
nut_solid = Solid(nut.wrapped)

result = cq.Workplane("XY").box(30, 30, 8).add(bolt_solid.translate((0, 0, 8)))
cq.exporters.export(result, "bracket.stl", tolerance=0.01, angularTolerance=0.1)
