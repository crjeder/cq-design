#!/usr/bin/env python3
"""Report whether cq-design is installed both as a plugin and as a standalone skill.

Usage:
    python src/install_check.py [--json] [--config-dir DIR] [--skills-dir DIR]

Read-only. Always exits 0; callers read `duplicate`. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

NAME = "cq-design"


def _commit(path: Path) -> str | None:
    """Commit of an install: `.version.json`, else live git HEAD of the (resolved) dir."""
    try:
        return json.loads((path / ".version.json").read_text(encoding="utf-8")).get("commit")
    except (OSError, ValueError, AttributeError):
        pass
    try:
        out = subprocess.run(
            ["git", "-C", str(path.resolve()), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def find_plugin(config_dir: Path) -> dict | None:
    """The cq-design entry in Claude Code's plugin registry whose installPath exists."""
    try:
        plugins = json.loads((config_dir / "plugins" / "installed_plugins.json").read_text("utf-8"))
        plugins = plugins["plugins"]
        for key, entries in plugins.items():
            if key.split("@")[0] != NAME:
                continue
            for entry in entries:
                path = Path(entry["installPath"])
                if path.is_dir():
                    return {"path": str(path), "commit": entry.get("gitCommitSha") or _commit(path)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def find_standalone(skills_dir: Path) -> dict | None:
    """The standalone skill copy (`<skills dir>/cq-design/SKILL.md`)."""
    path = skills_dir / NAME
    if not (path / "SKILL.md").is_file():
        return None
    return {"path": str(path), "commit": _commit(path)}


def check(config_dir: Path, skills_dir: Path) -> dict:
    """Both-installed report; see the duplicate-install-detection spec."""
    plugin, standalone = find_plugin(config_dir), find_standalone(skills_dir)
    duplicate = False
    differ = None
    hint = ""
    if plugin is not None and standalone is not None:
        duplicate = True
        if plugin["commit"] and standalone["commit"]:
            differ = plugin["commit"] != standalone["commit"]
        hint = (
            f"cq-design is installed twice: plugin at {plugin['path']} and standalone skill at "
            f"{standalone['path']}. Every skill, command and agent loads twice. Remove one: "
            "`/plugin uninstall cq-design` or `install.sh --uninstall` / `install.ps1 -Uninstall`."
        )
    return {
        "plugin": plugin,
        "standalone": standalone,
        "duplicate": duplicate,
        "commits_differ": differ,
        "hint": hint,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--skills-dir", type=Path)
    args = parser.parse_args(argv)

    config_dir = args.config_dir or Path(
        os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
    )
    skills_dir = args.skills_dir or Path(
        os.environ.get("CLAUDE_SKILLS_DIR") or config_dir / "skills"
    )
    result = check(config_dir, skills_dir)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["hint"] or "No duplicate cq-design install found.")
        if result["commits_differ"]:
            print("The two copies are at different commits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
