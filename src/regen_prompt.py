#!/usr/bin/env python3
"""Export a self-contained prompt that regenerates this project in a fresh LLM session.

Stdlib only. Serializes the durable intent artifacts of a finished project --
`BUILD_PLAN.json`'s approved `intent` and verbatim `request_log`, the sourced
measurements in `parameters.py`, the user-supplied images under `sketches/`, and
the print target -- into one Markdown file the user can paste into a new session
(improved model, newer skill, different skill) to rebuild the design from scratch.

The previous decomposition (parts, joints) is included as labelled reference, not
as a requirement: the point of regenerating is to let the new session decompose
the request itself.

Usage:
    python regen_prompt.py --plan BUILD_PLAN.json --out REGENERATE.md
    python regen_prompt.py --plan BUILD_PLAN.json          # writes to stdout

Exit codes: 0 success, 1 on error (missing file, invalid JSON).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HEADER = """# Regeneration prompt

Paste this whole file into a fresh session as the request. It is the complete,
current statement of what is being built -- design it from scratch; do not
assume any earlier session's files are available.
"""


def _request_history(entries: list[dict]) -> list[str]:
    out = ["## Request history (verbatim user wording, oldest first)", ""]
    for e in entries:
        meta = [e.get("kind", "?"), e.get("ts", "")]
        if e.get("level"):
            meta.append(f"level: {e['level']}")
        if e.get("targets"):
            meta.append("targets: " + ", ".join(e["targets"]))
        out.append(f"- **{' | '.join(m for m in meta if m)}**")
        for line in e.get("text", "").splitlines() or [""]:
            out.append(f"  > {line}")
        for img in e.get("images") or []:
            out.append(f"  - image: `{img}`")
        out.append("")
    return out


def _decomposition(plan: dict) -> list[str]:
    out = [
        "## Previous decomposition (reference only -- re-derive it, don't copy it)",
        "",
        "| part | description | dimensions (mm) |",
        "| --- | --- | --- |",
    ]
    for part in plan.get("parts") or []:
        dims = ", ".join(f"{k}={v}" for k, v in (part.get("dimensions") or {}).items())
        desc = (part.get("description") or "").replace("|", r"\|")
        out.append(f"| `{part.get('id')}` | {desc} | {dims} |")
    out.append("")
    joints = plan.get("joints") or []
    if joints:
        out.append("Joints:")
        out.append("")
        for j in joints:
            members = " + ".join(
                f"{m.get('part')}.{m.get('member')}" for m in j.get("members") or []
            )
            out.append(f"- `{j.get('joint_id')}`: {j.get('block')} -- {members}")
        if plan.get("root_part"):
            out.append(f"- assembly root part: `{plan['root_part']}`")
        out.append("")
    return out


def _rationale(plan: dict) -> list[str]:
    parts = [p for p in (plan.get("parts") or []) if p.get("engineering_rationale")]
    if not parts:
        return []
    out = ["## Engineering rationale", ""]
    for part in parts:
        rationale = part["engineering_rationale"]
        out.append(f"- `{part.get('id')}`:")
        if isinstance(rationale, str):
            out.append(f"  {rationale}")
        else:
            out.append(f"  - load path: {rationale.get('load_path')}")
            out.append(f"  - worst-case stress: {rationale.get('worst_case_stress')}")
            out.append(f"  - check: {rationale.get('check')}")
    out.append("")
    return out


def render(
    plan: dict, *, parameters_src: str | None = None, sketches: list[str] | None = None
) -> str:
    """Render the regeneration prompt Markdown from a plan and its side artifacts."""
    lines = [_HEADER, "## What to build", "", plan.get("intent", "").strip(), ""]

    entries = plan.get("request_log") or []
    if entries:
        lines += _request_history(entries)

    if parameters_src:
        lines += [
            "## Sourced measurements (`parameters.py`, with provenance)",
            "",
            "```python",
            parameters_src.rstrip(),
            "```",
            "",
        ]

    if sketches:
        lines += [
            "## User-supplied drawings",
            "",
            "Re-attach these image files to the new session -- the design depends on them:",
            "",
        ]
        lines += [f"- `{s}`" for s in sketches]
        lines.append("")

    target = [
        f"- printer: {plan.get('printer')}",
        f"- material: {plan.get('material')}",
        f"- nozzle: {plan.get('nozzle_mm')} mm",
    ]
    if plan.get("optimize_for"):
        target.append(f"- optimize for: {plan['optimize_for']}")
    for key, value in (plan.get("constraints") or {}).items():
        target.append(f"- {key}: {value}")
    lines += ["## Print target", "", *target, ""]

    lines += _decomposition(plan)
    lines += _rationale(plan)
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", default="BUILD_PLAN.json", help="Path to BUILD_PLAN.json")
    parser.add_argument("--out", help="Output path (default: stdout)")
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"regen_prompt: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"regen_prompt: invalid JSON: {exc}", file=sys.stderr)
        return 1

    root = plan_path.parent
    params = root / "parameters.py"
    sketches = sorted(
        p.relative_to(root).as_posix() for p in (root / "sketches").glob("*") if p.is_file()
    )
    text = render(
        plan,
        parameters_src=params.read_text(encoding="utf-8") if params.exists() else None,
        sketches=sketches,
    )

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
