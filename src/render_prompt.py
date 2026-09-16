#!/usr/bin/env python3
"""Render the builder, auditor, planner, or research agent prompt.

Usage:
    python render_prompt.py builder --plan BUILD_PLAN.json --part lid \
        [--override autonomous|staged] [--attempts build/attempts.jsonl] [--out PATH]
    python render_prompt.py audit --plan BUILD_PLAN.json --part lid \
        --script build/lid.py --previews preview/lid_preview.png ... [--out PATH]
    python render_prompt.py planning --request-file build/request.md \
        [--plan BUILD_PLAN.json] [--profile printer_profile.json] [--out PATH]
    python render_prompt.py research --targets-file build/lookup_targets.md \
        [--known-file build/known_context.md] [--out PATH]
    python render_prompt.py sourcing --request-file build/request.md [--out PATH]

Writes the prompt to --out (default build/<part>_prompt.txt / build/<part>_audit_prompt.txt /
build/planning_prompt.txt / build/research_prompt.txt / build/sourcing_prompt.txt) and
prints {"out", "chars", ...} as JSON. Exit 1 on an unknown part or unfilled placeholder.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

from plan_validate import _is_load_bearing
from printer_profile_validate import validate_profile
from request_log_search import search_request_log
from telemetry import _read_records, fold_attempts

SKILL_DIR = Path(__file__).resolve().parent.parent
REF = SKILL_DIR / "reference"
WALL_AXIS = {
    "north": "y", "south": "y", "east": "x", "west": "x",
    "top": "z", "bottom": "z", "up": "z", "down": "z",
}  # fmt: skip
TEXT_RE = re.compile(r"text|engrave|emboss|label", re.IGNORECASE)
LOAD_SECTIONS = {"Snap-Fit Strain Formula", "Rib / Boss / Gusset Ratios"}
MIN_INTENT_CHARS = 120
MAX_SECTIONS = 3


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def block_name(block: str | dict) -> str:
    return block if isinstance(block, str) else block["name"]


def union_ids(part: dict) -> set[str]:
    return {u["id"] for u in part.get("unions") or []} or {part["id"]}


def tagged_sections(
    md: str, blocks: set[str], extra_titles: frozenset[str] | set[str] = frozenset()
) -> str:
    """`## ` sections whose applies_to tag is `always`, names a block, or whose title is extra."""
    kept = []
    for chunk in re.split(r"(?m)^(?=## )", md)[1:]:
        title = chunk.splitlines()[0][3:].strip()
        tag = re.search(r"<!--\s*applies_to:\s*(.*?)\s*-->", chunk)
        tags = {t.strip() for t in tag.group(1).split(",")} if tag else set()
        if "always" in tags or tags & blocks or title in extra_titles:
            kept.append(chunk.rstrip())
    return "\n\n".join(kept) or "(none)"


def scoped_request(plan: dict, part: dict) -> str | None:
    """Approved intent (or the initial entry) plus request_log entries scoped to this part."""
    log = plan.get("request_log") or []
    intent = plan.get("intent") or ""
    if len(intent) < MIN_INTENT_CHARS:
        intent = next((e["text"] for e in log if e.get("kind") == "initial"), "")
    if not intent and not log:
        return None
    pid = part["id"]
    names = [i["name"] for i in part.get("interfaces") or [] if i.get("name")]
    queried = {id(e) for q in [pid, *names] for e in search_request_log(plan, query=q)}
    scoped = [
        e
        for e in log
        if e.get("kind") != "initial"
        and (
            any(t == pid or t.startswith(pid + ".") for t in e.get("targets") or [])
            or (not e.get("targets") and id(e) in queried)
        )
    ]
    lines = [f"Intent: {intent}"] if intent else []
    lines += [f"- [{e['kind']}] {e['text']}" for e in scoped]
    return "\n".join(lines)


def section_cuts(plan: dict, part: dict) -> list[str]:
    """Up to 3 `axis=value` cuts through named+positioned interfaces, request-mentioned first."""
    log = plan.get("request_log") or []
    pid = part["id"]
    ranked = []
    for order, itf in enumerate(part.get("interfaces") or []):
        name, pos = itf.get("name"), itf.get("position_mm")
        if not name or not pos:
            continue
        hits = [
            ({"clarification": 1, "correction": 2}.get(e.get("kind"), 3), -idx)
            for idx, e in enumerate(log)
            if (
                name in e["targets"] or f"{pid}.{name}" in e["targets"]
                if e.get("targets")
                else name.lower() in e.get("text", "").lower()
            )
        ]
        key = min(hits) if hits and min(hits)[0] < 3 else (3, order)
        # ponytail: axis falls back to the largest |position| component;
        # exact needs the bbox center, which only exists after the build
        axis = (
            WALL_AXIS.get(str(itf.get("wall", "")).lower())
            or "xyz"[max(range(3), key=lambda i: abs(pos[i]))]
        )
        ranked.append((key, f"{axis}={pos['xyz'.index(axis)]:g}"))
    ranked.sort(key=lambda r: r[0])
    return [cut for _, cut in ranked[:MAX_SECTIONS]]


def part_author_model() -> str:
    """`models.part_author` from ./skill_config.json, else the seeded default."""
    for path in (Path("skill_config.json"), SKILL_DIR / "src/skill_config.default.json"):
        if path.is_file():
            model = json.loads(_read(path)).get("models", {}).get("part_author")
            if model and model != "inline":
                return model
    return "unknown"


def validate_args(plan: dict, part: dict) -> str:
    dims = part["dimensions"]
    cons = plan["constraints"]
    args = [
        f"--expected-dims {dims['w_mm']:g},{dims['d_mm']:g},{dims['h_mm']:g}",
        f"--dim-tolerance {cons['dimension_tolerance_mm']:g}",
        f"--wall-min {cons['wall_min_mm']:g}",
        "--preview --preview-dir preview --cross-sections",
        f"--attempts-log build/attempts.jsonl --model {part_author_model()}",
    ]
    for itf in part.get("interfaces") or []:
        if not itf.get("name"):
            continue
        if itf.get("position_mm"):
            center = ",".join(f"{v:g}" for v in itf["position_mm"])
            args.append(f'--callout "name={itf["name"]};center={center}"')
        else:
            args.append(f"--unlocated-name {itf['name']}")
    args += [f"--extra-section {cut}" for cut in section_cuts(plan, part)]
    return " ".join(args)


def stages(plan: dict, part: dict, override: str | None) -> list[str]:
    policy = plan.get("review_policy", "every_stage")
    complex_part = bool(part.get("interfaces")) or len(part.get("blocks_needed") or []) >= 3
    if override:
        staged = override == "staged"
    else:
        staged = policy == "every_stage" or (policy == "checkpoints" and complex_part)
    stub = policy != "minimal" and override != "autonomous"
    return (["profile_stub"] if stub else []) + (
        ["base_shape", "features", "finishing"] if staged else ["full"]
    )


def start_point(part: dict) -> str:
    index = json.loads(_read(SKILL_DIR / "templates" / "archetypes.json"))
    if part.get("archetype"):
        entry = next((a for a in index if a["name"] == part["archetype"]), None)
        if entry:
            return (
                f"Planned archetype `{entry['name']}` (`templates/{entry['file']}`): "
                f"{entry['use']} Confirm it fits the part specification; if it does not, "
                "author from scratch and record why in `decisions`."
            )
    lines = "\n".join(f"     - `{a['name']}` (`templates/{a['file']}`): {a['use']}" for a in index)
    return (
        "No planned archetype. If one of these fits the part specification, start from it; "
        "otherwise author from scratch and record in `decisions` why none fit:\n" + lines
    )


def pitfalls(attempts: Path | None) -> str:
    if not attempts:
        return ""
    counts: Counter[str] = Counter()
    seen_on: dict[str, str] = {}
    for rec in fold_attempts(_read_records(attempts)):
        for err in rec.get("error_types") or []:
            counts[err] += 1
            seen_on.setdefault(err, rec.get("part_id", "?"))
    recurring = [f"`{e}` x{n} (e.g. on {seen_on[e]})" for e, n in counts.items() if n >= 2]
    return ("Known pitfalls this session: " + "; ".join(recurring) + ".") if recurring else ""


def block_specs(part: dict) -> str:
    names = [block_name(b) for b in part.get("blocks_needed") or []]
    if not names:
        return "(none -- use raw CadQuery primitives)"
    inventory = {b["name"]: b for b in json.loads(_read(SKILL_DIR / "src/blocks/inventory.json"))}
    lines = []
    for name in names:
        b = inventory.get(name, {"use": "(not in inventory)", "params": {}})
        params = ", ".join(f"{k} ({v})" for k, v in b["params"].items())
        lines.append(f"- **{name}** -- {b['use']}\n  params: {params}")
    return "\n".join(lines)


def pose_intent(plan: dict, part: dict) -> str:
    for joint in plan.get("joints") or []:
        if (
            any(m["part"] == part["id"] for m in joint["members"])
            and plan.get("root_part") != part["id"]
        ):
            return "(mate-chained via joints: pose is derived, report `placement: null`)"
    return part.get("pose_intent") or "(none)"


def fill(template: str, values: dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders in one pass, so injected text is never re-scanned."""
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", template)) - values.keys())
    if left:
        raise ValueError(f"unfilled placeholders: {', '.join(left)}")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], template)


def part_spec(plan: dict, part: dict) -> str:
    blocks = {block_name(b) for b in part.get("blocks_needed") or []}
    textish = TEXT_RE.search(
        " ".join(
            [part["description"], part.get("part_notes", ""), json.dumps(part.get("interfaces"))]
        )
    )
    cq_ref = (
        _read(REF / "CadQuery Pattern Reference.md")
        + "\n\n"
        + _read(REF / "CadQuery Anti-Patterns.md")
    )
    if textish:
        cq_ref += "\n\n" + _read(REF / "emboss_text.md")
    inventory = {b["name"]: b for b in json.loads(_read(SKILL_DIR / "src/blocks/inventory.json"))}
    modules = {inventory[b]["module"] for b in blocks if b in inventory}
    if modules & {"blocks.fasteners", "blocks.hardware"}:
        cq_ref += "\n\n" + _read(REF / "hardware_dims.md")
    if "blocks.gridfinity" in modules or str(part.get("archetype", "")).startswith("gridfinity"):
        cq_ref += "\n\n" + _read(REF / "gridfinity.md")
    moving = {k["moving_union"] for k in plan.get("kinematics") or []}
    extra = set(LOAD_SECTIONS) if part.get("load") else set()
    if moving & union_ids(part):
        extra.add("Flush-Fold Hinge Standoff")
    dims = part["dimensions"]
    cons = plan["constraints"]
    return fill(
        _read(SKILL_DIR / "prompts/part.md"),
        {
            "PART_ID": part["id"],
            "PART_DESCRIPTION": part["description"],
            "W_MM": f"{dims['w_mm']:g}",
            "D_MM": f"{dims['d_mm']:g}",
            "H_MM": f"{dims['h_mm']:g}",
            "INTERFACES": json.dumps(part["interfaces"]) if part.get("interfaces") else "(none)",
            "UNIONS": ", ".join(sorted(union_ids(part)))
            if part.get("unions")
            else "(single union)",
            "POSE_INTENT": pose_intent(plan, part),
            "PART_NOTES": part.get("part_notes") or "(none)",
            "BLOCK_SPECS": block_specs(part),
            "WALL_MIN_MM": f"{cons['wall_min_mm']:g}",
            "OVERHANG_MAX_DEG": f"{cons['overhang_max_deg']:g}",
            "MATERIAL": plan["material"],
            "NOZZLE_MM": f"{plan['nozzle_mm']:g}",
            "RATIONALE_FORM": "object" if _is_load_bearing(part) else "string",
            "FDM_GUIDELINES": tagged_sections(
                _read(REF / "FDM 3D Print Design Guidelines.md"), blocks
            ),
            "ENGINEERING_RULES": tagged_sections(
                _read(REF / "Engineering Design Rules.md"), blocks, extra
            ),
            "CQ_REFERENCE": cq_ref,
        },
    )


def render_builder(
    plan: dict, part: dict, override: str | None, attempts: Path | None
) -> tuple[str, list[str]]:
    part_stages = stages(plan, part, override)
    text = fill(
        _read(SKILL_DIR / "prompts/builder.md"),
        {
            "PART_ID": part["id"],
            "SKILL_DIR": SKILL_DIR.as_posix(),
            "STAGES": " -> ".join(part_stages),
            "VALIDATE_ARGS": validate_args(plan, part),
            "START_POINT": start_point(part),
            "PITFALLS": pitfalls(attempts),
            "PART_SPEC": part_spec(plan, part),
        },
    )
    return text, part_stages


def parameters_block(script: Path) -> str:
    """Top-level call-free assignments of a part script, as source lines."""
    source = _read(script)
    tree = ast.parse(source)
    lines = [
        ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.Assign)
        and all(isinstance(t, ast.Name) for t in node.targets)
        and not any(isinstance(n, ast.Call) for n in ast.walk(node.value))
    ]
    return "\n".join(lines) or "(no parameters found)"


def render_audit(plan: dict, part: dict, script: Path, previews: list[str]) -> str:
    if _is_load_bearing(part):
        numeric = (
            "```python\n"
            + parameters_block(script)
            + "\n```\n\nengineering_rationale: "
            + json.dumps(part.get("engineering_rationale"))
        )
    else:
        numeric = "(not load-bearing: skip group 4)"
    return fill(
        _read(SKILL_DIR / "prompts/audit.md"),
        {
            "PART_ENTRY": "```json\n" + json.dumps(part, indent=2) + "\n```",
            "REQUEST_TEXT": scoped_request(plan, part) or "(none)",
            "PARAMETERS_BLOCK": numeric,
            "PREVIEW_PATHS": "\n".join(f"- {p}" for p in previews),
        },
    )


def _index_lines(entries: list[dict], with_file: bool) -> str:
    if with_file:
        return "\n".join(
            f"- **{e['name']}** (`templates/{e['file']}`) -- {e['use']}" for e in entries
        )
    return "\n".join(f"- **{e['name']}** -- {e['use']}" for e in entries)


NO_PROFILE_NOTE = (
    "(none -- take printer, material, nozzle, and constraints from the user's Phase 1 answers)"
)


def render_planning(
    request: str, plan: dict | None, profile_path: Path
) -> tuple[str, str, list[str]]:
    """Returns (rendered text, profile status, profile errors)."""
    inventory = json.loads(_read(SKILL_DIR / "src/blocks/inventory.json"))
    archetypes = json.loads(_read(SKILL_DIR / "templates/archetypes.json"))
    blocks = {
        block_name(b)
        for part in (plan or {}).get("parts", [])
        for b in part.get("blocks_needed") or []
    }
    fdm = tagged_sections(_read(REF / "FDM 3D Print Design Guidelines.md"), blocks)

    profile_errors: list[str] = []
    if not profile_path.is_file():
        status = "absent"
        profile_text = NO_PROFILE_NOTE
    else:
        profile_errors = validate_profile(str(profile_path))
        if profile_errors:
            status = "invalid"
            profile_text = NO_PROFILE_NOTE
        else:
            profile = json.loads(_read(profile_path))
            status = "loaded"
            profile_text = json.dumps(
                {k: profile[k] for k in ("printer", "material", "nozzle_mm", "constraints")},
                indent=2,
            )

    text = fill(
        _read(SKILL_DIR / "prompts/planning.md"),
        {
            "USER_REQUEST": request,
            "BLOCK_INVENTORY": _index_lines(inventory, with_file=False),
            "ARCHETYPE_INDEX": _index_lines(archetypes, with_file=True),
            "FDM_GUIDELINES": fdm,
            "PRINTER_PROFILE": profile_text,
        },
    )
    return text, status, profile_errors


def render_research(targets: str, known: str | None) -> str:
    return fill(
        _read(SKILL_DIR / "prompts/research.md"),
        {
            "LOOKUP_TARGETS": targets,
            "KNOWN_CONTEXT": known.strip() if known and known.strip() else "(none)",
            "SKILL_DIR": SKILL_DIR.as_posix(),
        },
    )


def sourcing_corpus() -> str:
    """The 'Phase 0 sourcing corpus' section of documentation/Block_Sources.md."""
    md = _read(SKILL_DIR / "documentation/Block_Sources.md")
    section = re.search(r"(?m)^## 2\. Phase 0 sourcing corpus\n(.*)", md, re.DOTALL)
    return section.group(1).strip() if section else "(none)"


def render_sourcing(request: str) -> str:
    return fill(
        _read(SKILL_DIR / "prompts/sourcing.md"),
        {
            "REQUEST_TEXT": request,
            "SOURCING_CORPUS": sourcing_corpus(),
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="kind", required=True)
    for name in ("builder", "audit"):
        p = sub.add_parser(name)
        p.add_argument("--plan", required=True)
        p.add_argument("--part", required=True)
        p.add_argument("--out")
    sub.choices["builder"].add_argument("--override", choices=["autonomous", "staged"])
    sub.choices["builder"].add_argument("--attempts", type=Path)
    sub.choices["audit"].add_argument("--script", required=True, type=Path)
    sub.choices["audit"].add_argument("--previews", required=True, nargs="+")

    p = sub.add_parser("planning")
    p.add_argument("--request-file", required=True, type=Path)
    p.add_argument("--plan", type=Path)
    p.add_argument("--profile", type=Path, default=Path("printer_profile.json"))
    p.add_argument("--out")

    p = sub.add_parser("research")
    p.add_argument("--targets-file", required=True, type=Path)
    p.add_argument("--known-file", type=Path)
    p.add_argument("--out")

    p = sub.add_parser("sourcing")
    p.add_argument("--request-file", required=True, type=Path)
    p.add_argument("--out")

    args = parser.parse_args(argv)
    extra: dict[str, str | list[str]] = {}

    if args.kind in ("builder", "audit"):
        plan = json.loads(_read(Path(args.plan)))
        part = next((p for p in plan["parts"] if p["id"] == args.part), None)
        if part is None:
            print(f"render_prompt: no part '{args.part}' in {args.plan}", file=sys.stderr)
            return 1
        try:
            if args.kind == "builder":
                text, part_stages = render_builder(plan, part, args.override, args.attempts)
                out = Path(args.out or f"build/{part['id']}_prompt.txt")
                extra["stages"] = part_stages
            else:
                text = render_audit(plan, part, args.script, args.previews)
                out = Path(args.out or f"build/{part['id']}_audit_prompt.txt")
        except ValueError as exc:
            print(f"render_prompt: {exc}", file=sys.stderr)
            return 1
    elif args.kind == "planning":
        plan = json.loads(_read(args.plan)) if args.plan else None
        try:
            text, status, errors = render_planning(_read(args.request_file), plan, args.profile)
        except ValueError as exc:
            print(f"render_prompt: {exc}", file=sys.stderr)
            return 1
        out = Path(args.out or "build/planning_prompt.txt")
        extra["profile"] = status
        if errors:
            extra["profile_errors"] = errors
    elif args.kind == "research":
        try:
            text = render_research(
                _read(args.targets_file), _read(args.known_file) if args.known_file else None
            )
        except ValueError as exc:
            print(f"render_prompt: {exc}", file=sys.stderr)
            return 1
        out = Path(args.out or "build/research_prompt.txt")
    else:
        try:
            text = render_sourcing(_read(args.request_file))
        except ValueError as exc:
            print(f"render_prompt: {exc}", file=sys.stderr)
            return 1
        out = Path(args.out or "build/sourcing_prompt.txt")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({"out": out.as_posix(), "chars": len(text), **extra}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
