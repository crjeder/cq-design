#!/usr/bin/env python3
"""Make a working directory a self-contained uv project that regenerates its plates.

Copies build_template.py to build/build.py, the build tooling into lib/, and the
project template (pyproject.toml, .python-version) to the root. Tooling is refreshed on
every run (files the skill no longer ships are pruned); pyproject.toml and
.python-version are written only when absent. Stamps .bundle_version.json and merges the
skill's permissions/hooks into .claude/settings.local.json. Then run `uv sync` and
`uv run python build/build.py` in the working directory.

Usage:
    python bundle_project.py [DIR]
    python bundle_project.py --check [DIR]   # current / behind / unknown; exit 0 only if current
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import init_permissions
import skill_version

SRC = Path(__file__).resolve().parent
STAMP = ".bundle_version.json"
BUNDLE_MODULES = (
    "mesh_io.py",
    "write_assembly.py",
    "deliverables.py",
    "estampo_export.py",
    "print_orientation.py",
    "print_finishing.py",
    "placement.py",
    "mate_chain.py",
    "units.py",
    "freshness.py",
    "cq_verify.py",
    "cq_compat.py",
    "probes.py",
    "plan_params.py",
    "log.py",
)
BUNDLE_PACKAGES = ("exporters", "blocks")


def _prune(root: Path) -> None:
    """Delete bundled files the skill no longer ships; never touch other lib/ files."""
    lib = root / "lib"
    try:
        old_modules = json.loads((root / STAMP).read_text(encoding="utf-8")).get("modules", [])
    except (OSError, ValueError):
        old_modules = []
    for name in set(old_modules) - set(BUNDLE_MODULES):
        (lib / name).unlink(missing_ok=True)
    for package in BUNDLE_PACKAGES:
        dest = lib / package
        if not dest.is_dir():
            continue
        for f in dest.rglob("*"):
            if (
                f.is_file()
                and "__pycache__" not in f.parts
                and not (SRC / package / f.relative_to(dest)).exists()
            ):
                f.unlink()


def _write_stamp(root: Path) -> None:
    info = skill_version.describe_installed()
    stamp = {
        "commit": info.get("commit"),
        "dirty": info.get("dirty"),
        "bundled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modules": list(BUNDLE_MODULES),
    }
    (root / STAMP).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")


def bundle(root: Path) -> None:
    """Copy build.py, lib/ tooling, and the uv project template into root."""
    (root / "build").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "build_template.py", root / "build" / "build.py")
    lib = root / "lib"
    lib.mkdir(exist_ok=True)
    _prune(root)
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
        template, dest = SRC / "project_template" / name, root / name
        if not dest.exists():
            shutil.copy(template, dest)
        elif dest.read_bytes() != template.read_bytes():
            print(f"Kept existing {name} (differs from the skill template)")
    _write_stamp(root)


def check(root: Path) -> str:
    """Return 'current', 'behind', or 'unknown' for root's bundle vs this skill."""
    try:
        stamped = json.loads((root / STAMP).read_text(encoding="utf-8")).get("commit")
    except (OSError, ValueError):
        return "unknown"
    here = skill_version.describe_installed().get("commit")
    if not stamped or not here:
        return "unknown"
    if stamped == here:
        return "current"
    # ancestry is only knowable when the skill is a git checkout/symlink
    diff = skill_version.compare({"commit": stamped}, skill_version.SKILL_ROOT)
    return "behind" if diff["status"] == "behind" else "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("dir", nargs="?", default=".", help="working directory (default: cwd)")
    parser.add_argument(
        "--check", action="store_true", help="report bundle staleness; change nothing"
    )
    args = parser.parse_args()
    root = Path(args.dir)
    if args.check:
        status = check(root)
        print(status)
        return 0 if status == "current" else 1
    bundle(root)
    init_permissions.merge_permissions(str(root))
    init_permissions.merge_hooks(str(root))
    print(f"Bundled build/build.py, lib/, pyproject.toml into {root.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
