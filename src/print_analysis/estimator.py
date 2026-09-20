"""Thin wrapper around klipper_estimator (https://github.com/Annex-Engineering/klipper_estimator)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_MIN_TIME = re.compile(r"Minimal time:.*\(([\d.]+)\)")


def estimate_time(
    gcode: str | Path,
    exe: str = "klipper_estimator",
    config_file: str | Path | None = None,
    moonraker_url: str | None = None,
    timeout: int = 300,
) -> float:
    """Return estimated motion time in seconds.

    Excludes macro time (PRINT_START), heat-up and homing; add an offset in the caller.
    TODO: verify the config flag names with `klipper_estimator --help`.
    """
    cmd = [exe]
    if config_file:
        cmd += ["--config_file", str(config_file)]
    if moonraker_url:
        cmd += ["--config_moonraker_url", moonraker_url]
    cmd += ["estimate", str(gcode)]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
    m = _MIN_TIME.search(res.stdout)
    if not m:
        raise RuntimeError(f"Could not parse klipper_estimator output:\n{res.stdout[:500]}")
    return float(m.group(1))
