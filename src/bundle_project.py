#!/usr/bin/env python3
"""Make a working directory a self-contained uv project that regenerates its plates.

Copies build_template.py to build/build.py, the build tooling into lib/, and the
project template (pyproject.toml, .python-version) to the root. Overwrites on every
run so a re-export picks up the current skill tooling. Then run `uv sync` and
`uv run python build/build.py` in the working directory.

Usage:
    python bundle_project.py [DIR]
"""

import argparse
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
BUNDLE_MODULES = (
    "mesh_io.py",
    "model_export.py",
    "print_orientation.py",
    "print_finishing.py",
    "placement.py",
    "mate_chain.py",
    "units.py",
    "freshness.py",
    "cq_verify.py",
    "cq_compat.py",
)
BUNDLE_PACKAGES = ("exporters", "blocks")


def bundle(root: Path) -> None:
    """Copy build.py, lib/ tooling, and the uv project template into root."""
    (root / "build").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "build_template.py", root / "build" / "build.py")
    lib = root / "lib"
    lib.mkdir(exist_ok=True)
    for module in BUNDLE_MODULES:
        shutil.copy(SRC / module, lib / module)
    for package in BUNDLE_PACKAGES:
        shutil.copytree(
            SRC / package,
            lib / package,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    for name in ("pyproject.toml", ".python-version"):
        shutil.copy(SRC / "project_template" / name, root / name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dir", nargs="?", default=".", help="working directory (default: cwd)")
    root = Path(parser.parse_args().dir)
    bundle(root)
    print(f"Bundled build/build.py, lib/, pyproject.toml into {root.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
