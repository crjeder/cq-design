from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .parser import iter_moves


@dataclass(slots=True)
class SlowSegment:
    layer: int
    feature: str
    tool: int
    start: tuple[float, float]
    end: tuple[float, float]
    length_mm: float
    min_speed_mm_s: float
    time_s: float


def find_slow_segments(
    gcode: str | Path,
    max_speed: float = 30.0,
    min_length: float = 2.0,
    top: int = 20,
) -> list[dict]:
    """Group consecutive extruding moves at or below `max_speed` (mm/s), same layer/feature/tool.

    Uses the commanded feedrate only. TODO: use `klipper_estimator dump-moves` for the
    planned (acceleration-limited) speed, and flag min-layer-time slowdowns separately.
    """
    segs: list[SlowSegment] = []
    cur: SlowSegment | None = None

    def flush() -> None:
        nonlocal cur
        if cur and cur.length_mm >= min_length:
            segs.append(cur)
        cur = None

    for m in iter_moves(gcode):
        slow = m.extruding and 0 < m.feed <= max_speed
        if not slow:
            flush()
            continue
        key = (m.layer, m.feature, m.tool)
        if cur and (cur.layer, cur.feature, cur.tool) != key:
            flush()
        dt = m.length / m.feed
        if cur is None:
            cur = SlowSegment(m.layer, m.feature, m.tool, (m.x0, m.y0), (m.x1, m.y1),
                              m.length, m.feed, dt)
        else:
            cur.end = (m.x1, m.y1)
            cur.length_mm += m.length
            cur.min_speed_mm_s = min(cur.min_speed_mm_s, m.feed)
            cur.time_s += dt
    flush()

    segs.sort(key=lambda s: s.time_s, reverse=True)
    out = []
    for s in segs[:top]:
        d = asdict(s)
        d["length_mm"] = round(s.length_mm, 1)
        d["time_s"] = round(s.time_s, 1)
        d["start"] = [round(v, 1) for v in s.start]
        d["end"] = [round(v, 1) for v in s.end]
        out.append(d)
    return out
