"""Archetype: enclosure body. Open-top hollow box with an optional 2x2 corner
screw-boss pattern for a self-tapping-screw lid. Mate with lid_screwed (or any
lid template) placed on top.

Step form: every size and position comes from this archetype's plan `part` in
templates/archetypes.json (copied into BUILD_PLAN.json), never from the script."""

from blocks import Part

part = Part("enclosure_body")
body = part.select("hollow_box", id="body")
part.resize(body)
part.place(body, op="base")

if part.has("boss"):
    boss = part.select("screw_boss", id="boss")
    part.resize(boss)
    part.place(boss, at=[(x, y, 0) for x, y, _ in part.positions("boss")], op="union")

result = part.result()
