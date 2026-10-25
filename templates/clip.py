"""Archetype: U-clip. A U-shaped spring clip: a solid closed base at one end (Y=0) with
two parallel arms extending in +Y, separated by a gap sized to grip a panel or rail edge
by friction/spring-back. Use for cable clips, panel edge trim, badge clips, and
rail-mount clips.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("clip")
outer = part.select("box", id="outer")
part.resize(outer)
part.place(outer, at=(0, part.param("outer", "d") / 2, 0), op="base")

# The gap starts one wall thickness in from the closed base and runs out the open end.
gap = part.select("box", id="gap")
part.resize(gap)
wall = (part.param("outer", "h") - part.param("gap", "h")) / 2
part.place(gap, at=(0, wall + part.param("gap", "d") / 2, wall), op="cut")

result = part.result()
