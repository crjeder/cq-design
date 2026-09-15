#!/usr/bin/env python3
"""Report which commit of cq-design is installed, and whether it's current.

Usage:
    python src/skill_version.py                  # describe this checkout
    python src/skill_version.py --json            # machine-readable
    python src/skill_version.py --compare <repo>  # also diff against <repo>'s HEAD

Three ways a skill directory can carry a version:
  1. `.version.json`, written by install.ps1/install.sh on a plain copy install --
     the commit that was copied, whether the source tree was dirty, and when.
  2. A symlink (`install.ps1 -Link` / `install.sh --link`) -- always as current as
     its target, so its live git HEAD is reported instead of a stamped file.
  3. Neither -- e.g. running straight from a source checkout with no install step.
     Reports that checkout's own live git HEAD.
Falls back to "unknown" only when none of these apply (e.g. a copy install from a
non-git source tree, before this script existed).

Stdlib only, matching script_lint.py / request_log_search.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = SKILL_ROOT / ".version.json"


def _git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _live_git_info(repo: Path) -> dict | None:
    commit = _git(repo, "rev-parse", "HEAD")
    if commit is None:
        return None
    return {
        "commit": commit,
        "commit_short": _git(repo, "rev-parse", "--short", "HEAD"),
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(_git(repo, "status", "--porcelain")),
    }


def describe_installed() -> dict:
    """Version info for SKILL_ROOT, tagged with how it was determined (`source`)."""
    if SKILL_ROOT.is_symlink():
        target = SKILL_ROOT.resolve()
        info = _live_git_info(target) or {}
        return {"source": "linked", "target": str(target), **info}
    if VERSION_FILE.is_file():
        try:
            return {
                "source": "version_file",
                **json.loads(VERSION_FILE.read_text(encoding="utf-8")),
            }
        except (json.JSONDecodeError, OSError) as exc:
            return {"source": "version_file", "error": f"{VERSION_FILE} unreadable: {exc}"}
    checkout_info = _live_git_info(SKILL_ROOT)
    if checkout_info is not None:
        return {"source": "checkout", **checkout_info}
    return {"source": "unknown"}


def compare(installed: dict, repo: Path) -> dict:
    """Diff `installed`'s commit against `repo`'s current HEAD."""
    repo_head = _git(repo, "rev-parse", "HEAD")
    if repo_head is None:
        return {"status": "error", "message": f"{repo} is not a git repository"}
    installed_commit = installed.get("commit")
    if not installed_commit:
        return {
            "status": "unknown",
            "message": "installed copy carries no commit to compare (source: "
            f"{installed.get('source')})",
            "repo_head": repo_head,
        }
    if installed_commit == repo_head:
        return {"status": "up_to_date", "commit": repo_head}
    if _git(repo, "merge-base", "--is-ancestor", installed_commit, "HEAD") is not None:
        behind = _git(repo, "rev-list", "--count", f"{installed_commit}..HEAD")
        return {
            "status": "behind",
            "commits_behind": int(behind) if behind else None,
            "installed_commit": installed_commit,
            "repo_head": repo_head,
        }
    return {
        "status": "diverged",
        "message": "installed commit is not an ancestor of repo HEAD "
        "(different branch, or not found in this checkout)",
        "installed_commit": installed_commit,
        "repo_head": repo_head,
    }


def _format(installed: dict, diff: dict | None) -> str:
    lines = [f"Installed at: {SKILL_ROOT}"]
    source = installed.get("source")
    if source == "linked":
        lines.append(f"Symlinked to: {installed.get('target')}")
    elif source == "version_file":
        lines.append("Stamped by a copy install (.version.json)")
    elif source == "checkout":
        lines.append("Running directly from a git checkout (no install step)")
    else:
        lines.append("Version unknown -- no .version.json, not a symlink, not a git checkout")

    if installed.get("commit_short"):
        lines.append(f"Commit: {installed['commit_short']} ({installed.get('branch', '?')})")
    elif installed.get("commit"):
        lines.append(f"Commit: {installed['commit']}")
    if installed.get("dirty"):
        lines.append("Warning: source tree had uncommitted changes when installed/checked")
    if installed.get("installed_at"):
        lines.append(f"Installed at (timestamp): {installed['installed_at']}")
    if "error" in installed:
        lines.append(f"Error: {installed['error']}")

    if diff is not None:
        status = diff.get("status")
        if status == "up_to_date":
            lines.append(f"Compare: up to date with repo HEAD ({diff['commit'][:12]})")
        elif status == "behind":
            n = diff.get("commits_behind")
            suffix = f" {n} commit(s) behind" if n is not None else " behind"
            lines.append(f"Compare:{suffix} repo HEAD ({diff['repo_head'][:12]})")
        elif status == "diverged":
            lines.append(f"Compare: {diff['message']}")
        else:
            lines.append(f"Compare: {diff.get('message', status)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--compare", metavar="REPO", help="repo checkout to diff the installed commit against"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    installed = describe_installed()
    diff = compare(installed, Path(args.compare)) if args.compare else None

    if args.json:
        print(json.dumps({"installed": installed, "compare": diff}, indent=2))
    else:
        print(_format(installed, diff))
    return 1 if diff is not None and diff.get("status") not in ("up_to_date",) else 0


if __name__ == "__main__":
    sys.exit(main())
