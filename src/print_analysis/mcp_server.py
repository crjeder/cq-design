"""Optional MCP server. Requires: pip install "mcp[cli]"."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .analysis import summarize
from .slow_segments import find_slow_segments

mcp = FastMCP("print-analysis")


@mcp.tool()
def estimate_print(
    gcode_path: str,
    materials: dict[str, str] | None = None,
    with_time: bool = False,
    estimator_config: str | None = None,
    moonraker_url: str | None = None,
    startup_offset_s: float = 0.0,
) -> dict:
    """Filament length/mass per tool (and print time if with_time) for a G-code file."""
    est = {"config_file": estimator_config, "moonraker_url": moonraker_url} if with_time else None
    mats = {int(k): v.upper() for k, v in (materials or {}).items()}
    return summarize(gcode_path, mats, startup_offset_s=startup_offset_s, estimator=est)


@mcp.tool()
def slow_segments(gcode_path: str, max_speed: float = 30.0, min_length: float = 2.0,
                  top: int = 20) -> list[dict]:
    """Slowest extrusion segments with layer, feature type, position and time share."""
    return find_slow_segments(gcode_path, max_speed, min_length, top)


if __name__ == "__main__":
    mcp.run()
