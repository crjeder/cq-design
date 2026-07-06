#!/usr/bin/env python3
"""Seed a working directory's .claude/settings.local.json with the cq-design skill's
permission allow-patterns, so the user is not prompted for each skill-issued tool call.
Also scaffolds the documented top-level working-directory tree (build/, stl/, preview/)
so it exists up front instead of appearing piecemeal as different pipeline scripts run.

The canonical pattern list lives in skill_permissions.json beside this file. The merge
is additive and order-preserving: existing entries and other settings keys are never
removed, reordered, or duplicated. Directory scaffolding is likewise idempotent.

Usage:
    python init_permissions.py [DIR]          # merge patterns + scaffold dirs (default: cwd)
    python init_permissions.py [DIR] --check  # report whether init already ran

Exit codes (merge mode): 0 always on success.
Exit codes (--check mode): 0 if the sentinel pattern is already present, 1 if not.
"""

import argparse
import json
import os
import sys
from typing import Any

_PERMISSIONS_PATH = os.path.join(os.path.dirname(__file__), "skill_permissions.json")


def load_canonical() -> dict[str, Any]:
    """Load the canonical permission spec (sentinel + allow list) from disk."""
    with open(_PERMISSIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def settings_path(working_dir: str) -> str:
    """Return the path to the project-local settings file under working_dir."""
    return os.path.join(working_dir, ".claude", "settings.local.json")


def _load_settings(path: str) -> dict[str, Any]:
    """Load a settings.local.json, returning an empty dict if it does not exist."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_initialized(working_dir: str, sentinel: str) -> bool:
    """True if the sentinel pattern is already present in working_dir's settings."""
    settings = _load_settings(settings_path(working_dir))
    allow = settings.get("permissions", {}).get("allow", [])
    return sentinel in allow


_SCAFFOLD_DIRS = ("build", "stl", "preview")


def scaffold_directories(working_dir: str) -> list[str]:
    """Create the documented top-level working-directory tree (build/, stl/, preview/).

    Idempotent: only creates directories that don't already exist. These would
    otherwise appear one at a time, lazily, as different pipeline scripts first
    need them (run_cadquery_model.py for build/, model_export.py for stl/,
    the preview renderer for preview/), so the layout is unpredictable mid-run.
    Returns the list of directories actually created.
    """
    created = []
    for name in _SCAFFOLD_DIRS:
        path = os.path.join(working_dir, name)
        if not os.path.isdir(path):
            os.makedirs(path)
            created.append(name)
    return created


def merge_permissions(working_dir: str) -> list[str]:
    """Merge the canonical patterns into working_dir's settings.local.json.

    Creates .claude/ and the file when absent. Appends only patterns not already
    present, preserving existing entries, their order, and all other settings keys.
    Returns the list of patterns actually added.
    """
    canonical = load_canonical()
    patterns = canonical["allow"]
    path = settings_path(working_dir)

    settings = _load_settings(path)
    permissions = settings.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])

    existing = set(allow)
    added = [p for p in patterns if p not in existing]
    allow.extend(added)

    if added or not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")

    return added


def main() -> int:
    """CLI entry point: merge patterns, or report init status with --check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dir", nargs="?", default=".", help="working directory (default: cwd)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 0 if init already ran, 1 otherwise; make no changes",
    )
    args = parser.parse_args()

    canonical = load_canonical()
    sentinel = canonical["sentinel"]

    if args.check:
        initialized = is_initialized(args.dir, sentinel)
        print("initialized" if initialized else "uninitialized")
        return 0 if initialized else 1

    added = merge_permissions(args.dir)
    if added:
        print(f"Added {len(added)} permission pattern(s) to {settings_path(args.dir)}:")
        for pattern in added:
            print(f"  {pattern}")
    else:
        print(f"No changes; all patterns already present in {settings_path(args.dir)}")

    created = scaffold_directories(args.dir)
    if created:
        noun = "directory" if len(created) == 1 else "directories"
        print(f"Created {len(created)} {noun}: {', '.join(created)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
