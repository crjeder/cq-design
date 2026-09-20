"""Minimal streaming G-code parser (G0/G1, G90/G91, M82/M83, G92, T<n>, ;TYPE:, layer markers)."""
from __future__ import annotations

import math
import re
import warnings
from pathlib import Path
from typing import Iterator

from .models import Move

_WORD = re.compile(r"([A-Za-z])\s*(-?\d*\.?\d+)")
_TOOL = re.compile(r"T(\d+)", re.I)


def _words(rest: str) -> dict[str, float]:
    return {m.group(1).upper(): float(m.group(2)) for m in _WORD.finditer(rest)}


def iter_moves(path: str | Path) -> Iterator[Move]:
    x = y = z = e = 0.0
    feed = 0.0
    abs_xyz = abs_e = True
    tool, layer, feature = 0, -1, "unknown"
    arcs = 0

    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            code, _, comment = raw.partition(";")
            comment = comment.strip()
            if comment.startswith("TYPE:"):
                feature = comment[5:].strip()
            elif comment == "LAYER_CHANGE":
                layer += 1
            elif comment.startswith("LAYER:") and comment[6:].lstrip("-").isdigit():
                layer = int(comment[6:])

            code = code.strip()
            if not code:
                continue
            cmd, _, rest = code.partition(" ")
            cmd = cmd.upper()

            if cmd == "G90":
                abs_xyz = True
            elif cmd == "G91":
                abs_xyz = False
            elif cmd == "M82":
                abs_e = True
            elif cmd == "M83":
                abs_e = False
            elif _TOOL.fullmatch(cmd):
                tool = int(cmd[1:])
            elif cmd == "G92":
                w = _words(rest)
                e = w.get("E", e)
                x, y, z = w.get("X", x), w.get("Y", y), w.get("Z", z)
            elif cmd in ("G2", "G3"):
                arcs += 1  # TODO: arc support (length + extrusion)
            elif cmd in ("G0", "G1"):
                w = _words(rest)
                if "F" in w:
                    feed = w["F"] / 60.0
                nx = (w["X"] if abs_xyz else x + w["X"]) if "X" in w else x
                ny = (w["Y"] if abs_xyz else y + w["Y"]) if "Y" in w else y
                nz = (w["Z"] if abs_xyz else z + w["Z"]) if "Z" in w else z
                de = 0.0
                if "E" in w:
                    de = (w["E"] - e) if abs_e else w["E"]
                    e = w["E"] if abs_e else e + w["E"]
                length = math.dist((x, y, z), (nx, ny, nz))
                if length or de:
                    yield Move(x, y, nx, ny, nz, length, de, feed, tool, layer, feature)
                x, y, z = nx, ny, nz

    if arcs:
        warnings.warn(f"{arcs} arc moves (G2/G3) skipped; results are incomplete", stacklevel=2)
