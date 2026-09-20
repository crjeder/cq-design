from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Move:
    x0: float
    y0: float
    x1: float
    y1: float
    z: float
    length: float   # mm, 3D path length
    e: float        # signed filament delta in mm (retraction < 0)
    feed: float     # commanded feedrate in mm/s
    tool: int
    layer: int
    feature: str    # value of the last ";TYPE:" comment

    @property
    def extruding(self) -> bool:
        return self.e > 0 and (self.x0 != self.x1 or self.y0 != self.y1)
