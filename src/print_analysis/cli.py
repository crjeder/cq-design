from __future__ import annotations

import argparse
import json
import sys

from .analysis import summarize
from .slow_segments import find_slow_segments


def _materials(items: list[str] | None) -> dict[int, str]:
    return {int(k): v.upper() for k, v in (i.split("=", 1) for i in items or [])}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="print_analysis")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summary", help="time + weight per tool")
    s.add_argument("gcode")
    s.add_argument("--material", action="append", metavar="TOOL=MAT", help="e.g. 0=PLA 1=PETG")
    s.add_argument("--diameter", type=float, default=1.75)
    s.add_argument("--time", action="store_true", help="run klipper_estimator")
    s.add_argument("--estimator-exe", default="klipper_estimator")
    s.add_argument("--estimator-config")
    s.add_argument("--moonraker-url")
    s.add_argument("--offset", type=float, default=0.0, help="startup/heat-up offset in s")

    q = sub.add_parser("slow", help="slowest extrusion segments")
    q.add_argument("gcode")
    q.add_argument("--max-speed", type=float, default=30.0)
    q.add_argument("--min-length", type=float, default=2.0)
    q.add_argument("--top", type=int, default=20)

    a = p.parse_args(argv)
    if a.cmd == "summary":
        est = None
        if a.time:
            est = {"exe": a.estimator_exe, "config_file": a.estimator_config,
                   "moonraker_url": a.moonraker_url}
        res = summarize(a.gcode, _materials(a.material), a.diameter, a.offset, est)
    else:
        res = find_slow_segments(a.gcode, a.max_speed, a.min_length, a.top)

    json.dump(res, sys.stdout, separators=(",", ":"))  # compact: token-efficient for LLM use
    print()
    return 0
