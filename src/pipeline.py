#!/usr/bin/env python3
"""Pipeline state machine: derive the build state, report allowed steps, refuse bad ones.

    python pipeline.py status [--route design|plan|edit] [--dir .]
    python pipeline.py can <milestone> [--route R] [--dir .]
    python pipeline.py advance <milestone> <text> [--route R] [--dir .]

State is derived on every call from `build/journal.md` (decisions) and the artifacts
(`BUILD_PLAN.json` part ids, `build/<id>.py` hashes); nothing is stored. A journal line
counts only if the latest line of every prerequisite milestone is valid and earlier, so a
later upstream milestone voids what was built on it. Output is JSON on stdout, exit 0/1,
errors shaped like run_cadquery_model.py's `{type, message, hint}`.

Stdlib only (no CadQuery). Contract: reference/scripts.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from freshness import script_hash
from log import append_line

ROUTES = ("design", "plan", "edit")
EDIT_STEPS = ["import", "modify", "verify", "export"]

# base milestone -> (needs_id, prerequisites, optional)
# Prerequisites are base names; "part_accepted:*" means every plan part.
MILESTONES: dict[str, tuple[bool, list[str], bool]] = {
    "phase0/rung_decision": (False, [], True),
    "phase0/sourcing_skipped": (False, [], True),
    "phase1/topology_confirmed": (False, [], True),
    "phase1/dimensions_approved": (False, [], False),
    "phase2/plan_written": (False, ["phase1/dimensions_approved"], False),
    "phase2/plan_approved": (False, ["phase2/plan_written"], False),
    "phase3/stub_approved": (True, ["phase2/plan_approved"], True),
    "phase3/escalation": (True, ["phase2/plan_approved"], True),
    "phase3/part_accepted": (True, ["phase2/plan_approved"], False),
    "phase3/design_approved": (False, ["phase3/part_accepted:*"], False),
    "phase3/orientation_chosen": (False, ["phase3/design_approved"], False),
    "phase3/assembly_written": (False, ["phase3/orientation_chosen"], False),
    "phase3/gate_result": (False, ["phase3/assembly_written"], False),
    "phase4/delivered": (False, ["phase3/gate_result"], False),
}
SOURCING = ("phase0/rung_decision", "phase0/sourcing_skipped")
PLAN_LAST = "phase2/plan_approved"
_LINE = re.compile(r"^- (\S+): (.*)$")
_SHA = re.compile(r"\bsha=([0-9a-f]{64})\b")
_RUNG = re.compile(r"^rung (\d)\b")
_B1 = re.compile(r"\bb1=(\w+:\d+(?:,\w+:\d+)*)")


def _err(type_: str, message: str, hint: str) -> dict:
    return {"type": type_, "message": message, "hint": hint}


def _split(key: str) -> tuple[str, str | None]:
    base, sep, pid = key.partition(":")
    return base, (pid if sep else None)


def _plan_part_ids(root: Path) -> list[str] | None:
    try:
        plan = json.loads((root / "BUILD_PLAN.json").read_text(encoding="utf-8"))
        return [p["id"] for p in plan["parts"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def plan_b1(plan: dict) -> dict[str, int]:
    """Planned through-hole count per part: sum of interfaces[].through_count.

    A part is listed when an interface declares through_count, or for every part under
    design_intent "cad" (missing counts as 0)."""
    cad = plan.get("design_intent") == "cad"
    out: dict[str, int] = {}
    for part in plan.get("parts", []):
        counts = [i["through_count"] for i in part.get("interfaces", []) if "through_count" in i]
        if counts or cad:
            out[part["id"]] = sum(counts)
    return out


def _read_journal(root: Path) -> list[tuple[str, str]]:
    """Journal lines of the current attempt (after the last phase0/restart)."""
    try:
        text = (root / "build" / "journal.md").read_text(encoding="utf-8")
    except OSError:
        return []
    lines = [(m[1], m[2]) for ln in text.splitlines() if (m := _LINE.match(ln))]
    for i in range(len(lines) - 1, -1, -1):
        if lines[i][0] == "phase0/restart":
            return lines[i + 1 :]
    return lines


def _evaluate(root: Path) -> dict:
    """Classify every journal line valid/void/stale. Core of the state machine."""
    lines = _read_journal(root)
    ids = _plan_part_ids(root)
    latest: dict[str, int] = {}  # key -> index of its latest line
    for i, (key, _) in enumerate(lines):
        latest[key] = i
    valid: dict[int, bool] = {}
    void: list[dict] = []
    stale: dict[str, str] = {}
    warnings: list[str] = []
    rung: int | None = None

    def need(key: str, i: int) -> str | None:
        j = latest.get(key)
        if j is None:
            return key
        return None if j < i and valid.get(j) else key

    for i, (key, text) in enumerate(lines):
        base, pid = _split(key)
        spec = MILESTONES.get(base)
        if spec is None:
            valid[i] = True  # unknown lines (e.g. restart) are ignored, not void
            continue
        reason = None
        if base == "phase0/rung_decision":
            m = _RUNG.match(text)
            if m:
                rung = int(m.group(1))
            else:
                reason = "text must start with 'rung <n>'"
        prereqs = list(spec[1])
        if base == "phase4/delivered" and rung == 3:
            prereqs = ["phase0/rung_decision"]
        for pre in prereqs:
            if reason:
                break
            if pre.endswith(":*"):
                if ids is None:
                    reason = "BUILD_PLAN.json missing or unreadable"
                    break
                missing = [f"{pre[:-1]}{p}" for p in ids if need(f"{pre[:-1]}{p}", i)]
                if missing:
                    reason = f"needs {', '.join(missing)}"
            elif need(pre, i):
                reason = f"needs {pre}"
        if not reason and base == "phase3/part_accepted" and latest[key] == i:
            m = _SHA.search(text)
            pid = pid or ""
            script = root / "build" / f"{pid}.py"
            if m is None:
                warnings.append(f"part_accepted:{pid} has no sha= (unverified)")
            elif not script.is_file():
                stale[pid] = "script missing"
            elif script_hash(str(script)) != m.group(1):
                stale[pid] = "script changed since acceptance"
            if pid in stale:
                valid[i] = False
                continue
        valid[i] = reason is None
        if reason:
            void.append({"milestone": key, "reason": reason})
    done = sorted(k for k, j in latest.items() if valid.get(j) and _split(k)[0] in MILESTONES)
    return {
        "lines": lines,
        "latest": latest,
        "valid": valid,
        "done": done,
        "void": void,
        "stale": stale,
        "warnings": warnings,
        "ids": ids,
        "rung": rung if _sourcing_rung_valid(lines, latest, valid) else None,
    }


def approved_b1(root: Path) -> dict[str, int]:
    """Per-part planned b1 recorded on the latest valid plan_approved line ({} if none)."""
    ev = _evaluate(root)
    j = ev["latest"].get(PLAN_LAST)
    if j is None or not ev["valid"].get(j):
        return {}
    m = _B1.search(ev["lines"][j][1])
    if m is None:
        return {}
    return {k: int(v) for k, v in (e.split(":") for e in m.group(1).split(","))}


def _sourcing_rung_valid(lines, latest, valid) -> bool:
    j = latest.get("phase0/rung_decision")
    return j is not None and valid.get(j, False)


def _sourcing(ev: dict) -> str:
    cands = [(ev["latest"][k], k) for k in SOURCING if ev["latest"].get(k) is not None]
    cands = [(j, k) for j, k in cands if ev["valid"].get(j)]
    if not cands:
        return "pending"
    _, key = max(cands)
    return "skipped" if key == "phase0/sourcing_skipped" else f"rung_{ev['rung']}"


def _check(ev: dict, key: str, route: str) -> list[dict]:
    """Errors blocking `key` now; empty list means allowed."""
    base, pid = _split(key)
    spec = MILESTONES.get(base)
    if spec is None or spec[0] != (pid is not None) or pid == "":
        return [
            _err(
                "unknown_milestone",
                f"unknown milestone '{key}'",
                "use a key from the milestone table in skill/resume.md",
            )
        ]
    if route == "edit":
        return [
            _err(
                "route_forbids",
                f"'{key}' is not used on the edit route",
                "the edit route has no plan, journal, orientation or gate",
            )
        ]
    if route == "plan" and base.startswith(("phase3/", "phase4/")):
        return [
            _err("route_forbids", f"'{key}' is after plan approval", "continue on the design route")
        ]
    if pid is not None and ev["ids"] is not None and pid not in ev["ids"]:
        return [
            _err(
                "unknown_milestone",
                f"part '{pid}' is not in BUILD_PLAN.json",
                "use a part id from the plan",
            )
        ]
    prereqs = list(spec[1])
    if base == "phase4/delivered" and _sourcing(ev) == "rung_3":
        prereqs = ["phase0/rung_decision"]
    done = set(ev["done"])
    missing: list[str] = []
    for pre in prereqs:
        if pre.endswith(":*"):
            if ev["ids"] is None:
                missing.append("BUILD_PLAN.json")
            else:
                missing += [f"{pre[:-1]}{p}" for p in ev["ids"] if f"{pre[:-1]}{p}" not in done]
        elif pre not in done:
            missing.append(pre)
    if base == "phase3/design_approved" and ev["stale"]:
        return [
            _err(
                "part_stale",
                f"parts changed since acceptance: {', '.join(sorted(ev['stale']))}",
                "re-run the part loop and re-accept them",
            )
        ]
    if missing:
        return [
            _err(
                "prerequisite_missing",
                f"'{key}' needs {', '.join(missing)}",
                "record the missing milestones first (pipeline.py status)",
            )
        ]
    return []


def _allowed_next(ev: dict, route: str) -> tuple[list[str], list[dict]]:
    done = set(ev["done"])
    src = _sourcing(ev)
    ids = ev["ids"] or []
    cand: list[str] = []
    if src == "pending" and "phase1/dimensions_approved" not in done:
        cand += list(SOURCING)
    if src != "rung_3":
        cand += ["phase1/dimensions_approved", "phase2/plan_written", PLAN_LAST]
        if "phase2/plan_approved" in done:
            cand += [f"phase3/part_accepted:{p}" for p in ids]
            cand += [
                "phase3/design_approved",
                "phase3/orientation_chosen",
                "phase3/assembly_written",
                "phase3/gate_result",
            ]
    cand.append("phase4/delivered")
    allowed, blocked = [], []
    for key in cand:
        if key in done:
            continue
        errs = _check(ev, key, route)
        if errs:
            blocked.append({"step": key, "missing": errs[0]["message"]})
        else:
            allowed.append(key)
    # blocked reporting is useful only for the next gate, not the whole tail
    return allowed, blocked[:3]


def part_scope(part_id: str, stages: list[str]) -> str:
    """Scope line for a builder prompt: its own steps, and what belongs to main."""
    return (
        f"Your scope is part `{part_id}`: run only your stages ({' -> '.join(stages)}). "
        "Never run the audit, print orientation, assembly, quality gate or export, and never "
        "write journal milestones: `pipeline.py` gates those in the main session."
    )


def status(root: Path, route: str) -> dict:
    """Build the status document for `route` in `root`."""
    if route == "edit":
        return {
            "route": "edit",
            "sourcing": "n/a",
            "done": [],
            "void": [],
            "stale_parts": [],
            "warnings": [],
            "skipped_phases": [],
            "allowed_next": list(EDIT_STEPS),
            "blocked": [],
            "approved_b1": {},
            "complete": False,
        }
    ev = _evaluate(root)
    src = _sourcing(ev)
    allowed, blocked = _allowed_next(ev, route)
    done = ev["done"]
    if route == "plan":
        allowed = [a for a in allowed if not a.startswith(("phase3/", "phase4/"))]
        blocked = [b for b in blocked if not b["step"].startswith(("phase3/", "phase4/"))]
        complete = PLAN_LAST in done
        allowed = [] if complete else allowed
    else:
        complete = "phase4/delivered" in done
    return {
        "route": route,
        "sourcing": src,
        "done": done,
        "void": ev["void"],
        "stale_parts": sorted(ev["stale"]),
        "warnings": ev["warnings"],
        "skipped_phases": ["phase1", "phase2", "phase3"] if src == "rung_3" else [],
        "allowed_next": allowed,
        "blocked": blocked,
        "approved_b1": approved_b1(root),
        "complete": complete,
    }


def can(root: Path, key: str, route: str) -> list[dict]:
    """Errors that forbid recording `key`; empty list means allowed."""
    if route == "edit":
        return _check({}, key, route)
    return _check(_evaluate(root), key, route)


def advance(root: Path, key: str, text: str, route: str) -> tuple[str | None, list[dict]]:
    """Validate then append the journal line. Returns (line, errors)."""
    errs = can(root, key, route)
    if errs:
        return None, errs
    base, pid = _split(key)
    if base == "phase3/part_accepted" and not _SHA.search(text):
        script = root / "build" / f"{pid}.py"
        if script.is_file():
            text = f"{text} sha={script_hash(str(script))}".strip()
    if base == PLAN_LAST and "b1=" not in text:
        try:
            plan = json.loads((root / "BUILD_PLAN.json").read_text(encoding="utf-8"))
            b1 = plan_b1(plan)
        except (OSError, ValueError, KeyError, TypeError):
            b1 = {}
        if b1:
            text = f"{text} b1={','.join(f'{k}:{v}' for k, v in b1.items())}".strip()
    journal = root / "build" / "journal.md"
    journal.parent.mkdir(parents=True, exist_ok=True)
    return append_line(journal, key, text), []


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "can", "advance"):
        p = sub.add_parser(name)
        if name != "status":
            p.add_argument("milestone")
        if name == "advance":
            p.add_argument("text")
        p.add_argument("--route", choices=ROUTES, default="design")
        p.add_argument("--dir", default=".")
    args = parser.parse_args(argv)
    root = Path(args.dir)
    if args.command == "status":
        out, ok = status(root, args.route), True
    elif args.command == "can":
        errs = can(root, args.milestone, args.route)
        out, ok = {"ok": not errs, "errors": errs}, not errs
    else:
        line, errs = advance(root, args.milestone, args.text, args.route)
        out, ok = {"ok": not errs, "line": line, "errors": errs}, not errs
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
