from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from .estimator import estimate_time
from .parser import iter_moves

# g/cm^3, typical values; override via profile if you need exact numbers
DENSITY = {"PLA": 1.24, "PETG": 1.27, "ABS": 1.04, "ASA": 1.07, "TPU": 1.21}


def mass_g(length_mm: float, diameter: float = 1.75, density: float = 1.24) -> float:
    return math.pi * (diameter / 2) ** 2 * length_mm / 1000.0 * density


def _hms(s: float) -> str:
    s = int(round(s))
    return f"{s // 3600}h{s % 3600 // 60:02d}m{s % 60:02d}s"


def summarize(
    gcode: str | Path,
    materials: dict[int, str] | None = None,
    diameter: float = 1.75,
    startup_offset_s: float = 0.0,
    estimator: dict | None = None,
) -> dict:
    """Per-tool filament use and (optionally) print time. `estimator` = kwargs for estimate_time."""
    materials = materials or {}
    length: dict[int, float] = defaultdict(float)
    for m in iter_moves(gcode):
        length[m.tool] += m.e

    tools = {}
    for t, l in sorted(length.items()):
        mat = materials.get(t, "PLA")
        tools[t] = {
            "material": mat,
            "length_mm": round(l, 1),
            "mass_g": round(mass_g(l, diameter, DENSITY[mat]), 2),
        }
    out: dict = {"tools": tools, "total_mass_g": round(sum(v["mass_g"] for v in tools.values()), 2)}

    if estimator is not None:
        t = estimate_time(gcode, **estimator) + startup_offset_s
        out["time_s"] = round(t)
        out["time"] = _hms(t)
    return out
