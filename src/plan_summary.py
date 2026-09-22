#!/usr/bin/env python3
"""Render the Phase 2 plan-summary checkpoint tables from BUILD_PLAN.json as Markdown.

Usage:
    python plan_summary.py BUILD_PLAN.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

REVIEW_POLICY_MEANING = {
    "every_stage": "every part shows a profile-stub checkpoint, then one per stage "
    "(base shape, features, finishing)",
    "checkpoints": "every part shows the stub checkpoint; only parts with an interface "
    "or 3+ blocks get per-stage checkpoints",
    "minimal": "no stub and no stage checkpoints",
}


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _load(part: dict) -> str:
    load = part.get("load")
    if not load:
        return "(none)"
    text = ",".join(f"{v:g}" for v in load["dir"]) if load.get("dir") else ""
    if load.get("type", "tension") != "tension" or not text:
        text = f"{text} {load.get('type', 'tension')}".strip()
    return text


def _blocks(part: dict) -> str:
    names = [b if isinstance(b, str) else b["name"] for b in part.get("blocks_needed") or []]
    return ", ".join(names) or "(none)"


def _tokens(text: str) -> set[str]:
    """Non-numeric word tokens (numeric suffixes like the '2' in hole_2 disambiguate,
    they don't need to match user wording)."""
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if not t.isdigit()}


def _open_questions(plan: dict) -> list[str]:
    lines = (plan.get("planning_notes") or "").split("\n")
    stripped = [re.sub(r"^[-*+]\s+", "", line.strip()) for line in lines]
    return [line for line in stripped if line.startswith("OPEN:")]


# `LOAD_MASS: <part_id> <mass> <unit> sf=<safety_factor>` in planning_notes, e.g.
# `LOAD_MASS: phone_shelf 187 g sf=2.0` -- same free-text-convention approach as
# `OPEN:`, carrying the mass/safety-factor derivation behind a part's `load.magnitude_n`
# without a schema field for it (the schema already carries the resulting magnitude_n).
_LOAD_MASS_RE = re.compile(
    r"^LOAD_MASS:\s+(?P<part_id>[a-z][a-z0-9_]*)\s+(?P<mass>[\d.]+)\s*(?P<unit>\S+)\s+sf=(?P<sf>[\d.]+)"
)


def _load_mass_notes(plan: dict) -> dict[str, dict[str, str]]:
    lines = (plan.get("planning_notes") or "").split("\n")
    stripped = [re.sub(r"^[-*+]\s+", "", line.strip()) for line in lines]
    notes: dict[str, dict[str, str]] = {}
    for line in stripped:
        m = _LOAD_MASS_RE.match(line)
        if m:
            notes[m.group("part_id")] = {
                "mass": m.group("mass"),
                "unit": m.group("unit"),
                "sf": m.group("sf"),
            }
    return notes


def _load_cases(plan: dict) -> list[list]:
    """One row per part declaring `load.magnitude_n`: the derivation (source mass, unit,
    safety factor) alongside the resulting force and anchors, so the Phase 2 checkpoint
    can catch a wrong mass before Phase 3 runs any FEM solve."""
    mass_notes = _load_mass_notes(plan)
    rows = []
    for p in plan["parts"]:
        load = p.get("load") or {}
        magnitude_n = load.get("magnitude_n")
        if magnitude_n is None:
            continue
        note = mass_notes.get(p["id"], {})
        mass = f"{note['mass']} {note['unit']}" if note else "(unspecified)"
        sf = note.get("sf", "(unspecified)")
        applied = load.get("applied_at") or "(none)"
        applied_dir = load.get("applied_dir")
        if applied_dir:
            applied += " dir=" + ",".join(f"{v:g}" for v in applied_dir)
        grounded = ", ".join(load.get("grounded_at") or []) or "(none)"
        rows.append([p["id"], mass, sf, f"{magnitude_n:g} N", applied, grounded])
    return rows


def _coined_names(plan: dict) -> list[str]:
    log_words: set[str] = set()
    for entry in plan.get("request_log") or []:
        log_words |= _tokens(entry.get("text", ""))
    if not log_words:
        return []
    flagged = []
    for part in plan["parts"]:
        if not _tokens(part["id"]) <= log_words:
            flagged.append(f"`{part['id']}` (part)")
        for i in part.get("interfaces") or []:
            name = i.get("name")
            if name and not _tokens(name) <= log_words:
                flagged.append(f"`{name}` (interface on `{part['id']}`)")
    return flagged


def summarize(plan: dict, plan_path: Path) -> str:
    """Markdown checkpoint tables for a validated plan."""
    parts = plan["parts"]
    out = [f"Written to: `{plan_path.resolve()}`", ""]
    out += [
        "**Printer / Material**",
        "",
        _table(
            ["Printer", "Material", "Nozzle"],
            [[plan.get("printer", ""), plan["material"], f"{plan['nozzle_mm']:g} mm"]],
        ),
        "",
        "**Parts**",
        "",
        _table(
            ["#", "ID", "Description", "W x D x H (mm)", "Load", "Pose", "Blocks", "Archetype"],
            [
                [
                    n,
                    p["id"],
                    p["description"],
                    " x ".join(f"{p['dimensions'][k]:g}" for k in ("w_mm", "d_mm", "h_mm")),
                    _load(p),
                    p.get("pose_intent", "(none)"),
                    _blocks(p),
                    p.get("archetype", "(none)"),
                ]
                for n, p in enumerate(parts, 1)
            ],
        ),
        "",
    ]

    goal = plan.get("optimize_for", "strength")
    line = f"**Print optimization:** `{goal}`"
    overrides = [
        f"`{p['id']}` -> `{p['optimize_for']}`"
        for p in parts
        if p.get("optimize_for", goal) != goal
    ]
    if overrides:
        line += "; overrides: " + ", ".join(overrides)
    faces = [
        f"`{p['id']}` show_face "
        + (",".join(f"{v:g}" for v in p["show_face"]["dir"]) if p.get("show_face") else "inferred")
        for p in parts
        if p.get("optimize_for", goal) == "visual_quality"
    ]
    if faces:
        line += "; " + ", ".join(faces)
    policy = plan.get("review_policy", "every_stage")
    out += [line, "", f"**Review policy:** `{policy}` -- {REVIEW_POLICY_MEANING[policy]}", ""]

    interfaces = [
        [
            p["id"],
            i.get("name") or "",
            i.get("type", ""),
            i.get("connector", ""),
            i.get("wall", ""),
            ",".join(f"{v:g}" for v in i["position_mm"]) if i.get("position_mm") else "",
        ]
        for p in parts
        for i in p.get("interfaces") or []
    ]
    if interfaces:
        out += [
            "**Interfaces**",
            "",
            _table(["Part", "Name", "Type", "Connector", "Wall", "Position (mm)"], interfaces),
            "",
        ]

    load_cases = _load_cases(plan)
    if load_cases:
        headers = [
            "Part",
            "Source mass",
            "Safety factor",
            "magnitude_n",
            "Applied at",
            "Grounded at",
        ]
        out += ["**Load cases**", "", _table(headers, load_cases), ""]

    coined = _coined_names(plan)
    if coined:
        out += ["**Names I chose**", "", *[f"- {c}" for c in coined], ""]

    open_questions = _open_questions(plan)
    if open_questions:
        out += ["**Open questions**", "", *[f"- {q}" for q in open_questions], ""]

    cons = plan["constraints"]
    out += [
        "**Constraints**",
        "",
        _table(
            ["Wall min", "Overhang max", "Dim tolerance"],
            [
                [
                    f"{cons['wall_min_mm']:g} mm",
                    f"{cons['overhang_max_deg']:g} deg",
                    f"{cons['dimension_tolerance_mm']:g} mm",
                ]
            ],
        ),
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="Path to BUILD_PLAN.json")
    path = Path(parser.parse_args().plan)
    print(summarize(json.loads(path.read_text(encoding="utf-8")), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
