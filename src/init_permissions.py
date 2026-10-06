#!/usr/bin/env python3
"""Seed a working directory's .claude/settings.local.json with the cq-design skill's
permission allow-patterns, so the user is not prompted for each skill-issued tool call.
Also scaffolds the documented top-level working-directory tree (build/, stl/, preview/)
so it exists up front instead of appearing piecemeal as different pipeline scripts run,
and seeds profile.json and skill_config.json from their defaults when absent.

The canonical pattern list lives in skill_permissions.json beside this file. The merge
is additive and order-preserving: existing entries and other settings keys are never
removed, reordered, or duplicated. Directory scaffolding is likewise idempotent.

Usage:
    python init_permissions.py [DIR]          # merge patterns + scaffold dirs (default: cwd)
    python init_permissions.py [DIR] --check  # report whether init already ran
    python init_permissions.py [DIR] --venv P # also set UV_PROJECT_ENVIRONMENT=P (plugin install)

Exit codes (merge mode): 0 always on success.
Exit codes (--check mode): 0 if the sentinel pattern is already present, 1 if not.
"""

import argparse
import json
import os
import re
import shutil
import sys
from typing import Any

_PERMISSIONS_PATH = os.path.join(os.path.dirname(__file__), "skill_permissions.json")
_SESSION_COST_PATH = os.path.join(os.path.dirname(__file__), "session_cost.py")
_LOG_PATH = os.path.join(os.path.dirname(__file__), "log.py")


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
    need them (run_cadquery_model.py for build/, write_assembly.py for stl/,
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


_SEEDED_FILES = {
    "profile.json": "profile.default.json",
    "skill_config.json": "skill_config.default.json",
}


def seed_default_files(working_dir: str) -> list[str]:
    """Copy each default config into working_dir when absent; never overwrite.

    Returns the file names actually created.
    """
    created = []
    for name, default in _SEEDED_FILES.items():
        path = os.path.join(working_dir, name)
        if not os.path.exists(path):
            shutil.copyfile(os.path.join(os.path.dirname(__file__), default), path)
            created.append(name)
    return created


def _resolve_command(command: str) -> str:
    """Substitute the `{session_cost_path}`/`{log_path}` placeholders."""
    return command.replace("{session_cost_path}", _SESSION_COST_PATH).replace(
        "{log_path}", _LOG_PATH
    )


def _resolved_hooks() -> dict[str, Any]:
    """The canonical `hooks` block with path placeholders resolved to absolute
    script paths. Keys starting with `_` (comments) are dropped."""
    hooks = load_canonical().get("hooks", {})
    resolved: dict[str, Any] = {}
    for event, groups in hooks.items():
        if event.startswith("_"):
            continue
        out_groups = []
        for group in groups:
            out_hooks = [
                {**h, "command": _resolve_command(h["command"])} if "command" in h else h
                for h in group.get("hooks", [])
            ]
            out_groups.append({**group, "hooks": out_hooks})
        resolved[event] = out_groups
    return resolved


def _drop_stale(groups: list[dict[str, Any]], new_commands: list[str]) -> bool:
    """Remove hooks that run the same script as a new command from another path."""
    tail = re.compile(r"[^\\/]+$")
    wanted = {m.group() for c in new_commands if (m := tail.search(c))}
    removed = False
    for group in groups:
        keep = []
        for h in group.get("hooks", []):
            cmd = h.get("command", "")
            m = tail.search(cmd)
            if m and m.group() in wanted and cmd not in new_commands:
                removed = True
            else:
                keep.append(h)
        group["hooks"] = keep
    groups[:] = [g for g in groups if g.get("hooks")]
    return removed


def merge_hooks(working_dir: str) -> bool:
    """Seed the canonical hooks (session-cost, telemetry, ...) into working_dir's
    settings.local.json.

    Idempotent: a canonical entry is added only when its resolved command isn't
    already present under that event. Entries are never reordered, and none are
    removed except a stale copy of a canonical hook (same script, old install
    path, e.g. after a plugin update), which is replaced. Returns True only when
    something changed.
    """
    resolved = _resolved_hooks()
    if not resolved:
        return False
    path = settings_path(working_dir)
    settings = _load_settings(path)
    hooks = settings.setdefault("hooks", {})

    changed = False
    for event, groups in resolved.items():
        existing = hooks.setdefault(event, [])
        new_commands = [h.get("command", "") for g in groups for h in g.get("hooks", [])]
        if _drop_stale(existing, new_commands):
            changed = True
        present = " ".join(h.get("command", "") for g in existing for h in g.get("hooks", []))
        if any(cmd and cmd in present for cmd in new_commands):
            continue
        existing.extend(groups)
        changed = True

    if changed:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
    return changed


def merge_env(working_dir: str, venv: str) -> bool:
    """Point uv at `venv` for Bash calls in working_dir (plugin installs keep it outside
    the plugin root). Returns True when the setting changed."""
    path = settings_path(working_dir)
    settings = _load_settings(path)
    env = settings.setdefault("env", {})
    if env.get("UV_PROJECT_ENVIRONMENT") == venv:
        return False
    env["UV_PROJECT_ENVIRONMENT"] = venv
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    return True


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
    parser.add_argument(
        "--venv",
        help="set UV_PROJECT_ENVIRONMENT to this path in the project's settings (plugin installs)",
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

    if args.venv and merge_env(args.dir, args.venv):
        print(f"Set UV_PROJECT_ENVIRONMENT={args.venv} in {settings_path(args.dir)}")

    if merge_hooks(args.dir):
        print(
            f"Seeded the session-cost Stop hook (build/cost.json) and the "
            f"telemetry PostToolUse hook (build/attempts.jsonl) in {settings_path(args.dir)}"
        )

    created = scaffold_directories(args.dir)
    if created:
        noun = "directory" if len(created) == 1 else "directories"
        print(f"Created {len(created)} {noun}: {', '.join(created)}")

    for name in seed_default_files(args.dir):
        print(f"Seeded {name} with defaults -- edit it to match your printer / model routing.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
