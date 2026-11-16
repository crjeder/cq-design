#!/usr/bin/env python3
"""Oracle acceptance statements: validate acceptance.json, check plan bindings, verify geometry.

The oracle agent turns the approved intent into frame-free statements (no coordinates) in
`acceptance.json` next to BUILD_PLAN.json. The planner binds each one to plan entities in
`acceptance_bindings`. This module checks three things:

- ``validate``: schema, unique ids, every statement cites the intent (or a parameters.py
  name), and every expression resolves.
- ``check``: every statement is bound and the bound plan entities agree with it
  (called by ``plan.py validate``).
- ``verify``: the built body satisfies each bound statement (called by the quality gate).

Usage:
    python3 oracle.py validate acceptance.json [--intent TEXT | --plan BUILD_PLAN.json]
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema

import plan_params

ACCEPTANCE_FILE = "acceptance.json"
DEFAULT_TOL_MM = 0.2
MAX_ROUNDS = 3

_NUM = {"type": ["number", "string"]}
_PAIR = {"type": "array", "items": _NUM, "minItems": 2, "maxItems": 2}
_BASE = {
    "id": {"type": "string", "pattern": "^S[1-9][0-9]*$"},
    "cites": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
    "text": {"type": "string", "minLength": 1},
    "tol_mm": _NUM,
}


def _kind(name: str, required: list[str], props: dict) -> dict:
    return {
        "type": "object",
        "required": ["id", "kind", "cites", "text", *required],
        "additionalProperties": False,
        "properties": {**_BASE, "kind": {"const": name}, **props},
    }


# Interface type families a `feature` statement may name; the bound interface's plan
# `type` must be in the family.
FAMILIES = {
    "hole": {"hole", "bore", "screw_hole", "screw_mount", "clearance_opening"},
    "slot": {"slot", "cable_slot", "port_cutout", "cutout", "clearance_opening"},
    "pocket": {"pocket", "nut_trap", "cutout"},
    "vent": {"vent_grid"},
    "boss": {"boss", "screw_boss", "pcb_standoff", "union"},
    "pin": {"pin", "post"},
}

SCHEMA = {
    "type": "object",
    "required": ["schema_version", "statements"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": 1},
        "statements": {
            "type": "array",
            "items": {
                "oneOf": [
                    _kind("part_count", ["n"], {"n": {"type": "integer", "minimum": 1}}),
                    _kind(
                        "feature",
                        ["feature", "count"],
                        {
                            "feature": {"enum": sorted(FAMILIES)},
                            "count": {"type": "integer", "minimum": 1},
                            "diameter_mm": _NUM,
                            "size_mm": _PAIR,
                        },
                    ),
                    _kind(
                        "fit",
                        ["accepts"],
                        {
                            "accepts": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {"diameter_mm": _NUM, "size_mm": _PAIR},
                                "minProperties": 1,
                                "maxProperties": 1,
                            },
                            "clearance_min_mm": _NUM,
                        },
                    ),
                    _kind(
                        "spacing",
                        ["distance_mm", "between"],
                        {
                            "distance_mm": _NUM,
                            "between": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                    ),
                    _kind(
                        "extent",
                        ["which"],
                        {
                            "which": {"enum": ["largest", "smallest", "any"]},
                            "max_mm": _NUM,
                            "min_mm": _NUM,
                        },
                    ),
                    _kind("probe", [], {}),
                    _kind("visual", [], {}),
                ]
            },
        },
    },
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def load(path: Path) -> dict | None:
    """acceptance.json as a dict, or None when the file does not exist."""
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def acceptance_for(plan_path: str | Path) -> Path:
    """Path of the acceptance.json that belongs to a plan file."""
    return Path(plan_path).resolve().parent / ACCEPTANCE_FILE


def _value(raw: Any, consts: dict[str, float]) -> float:
    return plan_params.evaluate(raw, consts) if isinstance(raw, str) else float(raw)


def _expressions(s: dict) -> list[Any]:
    keys = ("diameter_mm", "distance_mm", "max_mm", "min_mm", "clearance_min_mm", "tol_mm")
    acc = s.get("accepts") or {}
    vals = [s.get(k) for k in keys] + list(s.get("size_mm") or [])
    vals += [acc.get("diameter_mm"), *(acc.get("size_mm") or [])]
    return [v for v in vals if v is not None]


def _is_param(cite: str, consts: dict[str, float] | None) -> bool:
    """A parameters.py name; before parameters.py exists (Phase 1) any UPPER_CASE name."""
    if consts is None:
        return re.fullmatch(r"[A-Z][A-Z0-9_]*", cite) is not None
    return cite in consts


def validate(doc: Any, intent: str | None, consts: dict[str, float] | None) -> list[str]:
    """Schema, ids, citations (when `intent` is given), expressions (when `consts` is given)."""
    errors = [
        f"acceptance.json {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
        for e in jsonschema.Draft7Validator(SCHEMA).iter_errors(doc)
    ]
    if errors:
        return errors
    seen: set[str] = set()
    norm_intent = _norm(intent) if intent is not None else None
    for s in doc["statements"]:
        sid = s["id"]
        if sid in seen:
            errors.append(f"oracle: duplicate statement id {sid}")
        seen.add(sid)
        if norm_intent is not None and not any(
            _norm(c) in norm_intent or _is_param(c, consts) for c in s["cites"]
        ):
            errors.append(f"oracle: {sid} ({s['text']!r}) cites nothing found in the intent")
        if consts is not None:
            for raw in _expressions(s):
                try:
                    _value(raw, consts)
                except plan_params.PlanParamError as exc:
                    errors.append(f"oracle: {sid} expression {raw!r}: {exc}")
    return errors


def _tol(s: dict, consts: dict[str, float]) -> float:
    return _value(s["tol_mm"], consts) if "tol_mm" in s else DEFAULT_TOL_MM


def _width(itf: dict) -> list[float]:
    if itf.get("diameter_mm") is not None:
        return [float(itf["diameter_mm"])]
    return sorted(float(v) for v in itf.get("size_mm") or [])


def _wanted_width(src: dict, consts: dict[str, float]) -> list[float] | None:
    if "diameter_mm" in src:
        return [_value(src["diameter_mm"], consts)]
    if "size_mm" in src:
        return sorted(_value(v, consts) for v in src["size_mm"])
    return None


def _bound_probes(b: dict, part: dict) -> list[dict]:
    labels = set(b.get("probes") or [])
    return [p for p in part.get("probes") or [] if p.get("label") in labels]


def _extent_errors(s: dict, extents: list[float], consts: dict[str, float]) -> list[str]:
    tol = _tol(s, consts)
    ext = sorted(extents)
    picked = {"largest": [ext[-1]], "smallest": [ext[0]], "any": ext}[s["which"]]
    # "any": at least one extent must satisfy the bound
    need = len(picked) if s["which"] == "any" else 1
    errors = []
    if "max_mm" in s:
        hi = _value(s["max_mm"], consts)
        over = [e for e in picked if e > hi + tol]
        if len(over) >= need:
            errors.append(f"{s['which']} extent {min(over):g} mm exceeds {hi:g} mm")
    if "min_mm" in s:
        lo = _value(s["min_mm"], consts)
        under = [e for e in picked if e < lo - tol]
        if len(under) >= need:
            errors.append(f"{s['which']} extent {max(under):g} mm is below {lo:g} mm")
    return errors


def _check_one(
    s: dict, b: dict, part: dict, itfs: list[dict], consts: dict[str, float]
) -> list[str]:
    kind, tol = s["kind"], _tol(s, consts)
    if kind == "feature":
        if len(itfs) != s["count"]:
            return [f"expects {s['count']} bound interfaces, found {len(itfs)}"]
        bad = [i.get("name") for i in itfs if i.get("type") not in FAMILIES[s["feature"]]]
        if bad:
            return [f"interfaces {bad} are not of feature family {s['feature']!r}"]
        size = _wanted_width(s, consts)
        if size is None:
            return []
        for i in itfs:
            width = _width(i)
            if len(width) != len(size) or any(
                abs(g - w) > tol for g, w in zip(width, size, strict=True)
            ):
                return [f"interface {i.get('name')!r} size {width} != {size} (tol {tol:g})"]
        return []
    if kind == "fit":
        if len(itfs) != 1:
            return [f"expects 1 bound interface, found {len(itfs)}"]
        want = _wanted_width(s["accepts"], consts) or []
        clear = _value(s.get("clearance_min_mm", 0), consts)
        got = _width(itfs[0])
        if len(got) != len(want) or any(g < w + clear for g, w in zip(got, want, strict=True)):
            return [
                f"interface {itfs[0].get('name')!r} size {got} does not accept {want} "
                f"with clearance >= {clear:g}"
            ]
        return []
    if kind == "spacing":
        if len(itfs) != 2:
            return [f"expects 2 bound interfaces, found {len(itfs)}"]
        if any("position_mm" not in i for i in itfs):
            return ["both bound interfaces need position_mm"]
        dist = math.dist(itfs[0]["position_mm"], itfs[1]["position_mm"])
        expected = _value(s["distance_mm"], consts)
        if abs(dist - expected) > tol:
            return [f"spacing {dist:.2f} mm != expected {expected:g} mm (tol {tol:g})"]
        return []
    if kind == "extent":
        dims = part.get("dimensions") or {}
        return _extent_errors(s, [dims.get(k, 0) for k in ("w_mm", "d_mm", "h_mm")], consts)
    if kind == "probe" and not any(
        p.get("label", "").startswith(s["id"]) for p in _bound_probes(b, part)
    ):
        return [f"no bound probe labelled '{s['id']}: ...'"]
    return []


def check(plan: dict, doc: dict, consts: dict[str, float]) -> list[str]:
    """Plan-time binding errors, one string per problem, each naming the statement."""
    errors = validate(doc, plan.get("intent"), consts)
    if errors:
        return errors
    statements = {s["id"]: s for s in doc["statements"]}
    parts = {p["id"]: p for p in plan.get("parts", [])}
    bound: dict[str, list[dict]] = {}
    for b in plan.get("acceptance_bindings") or []:
        if b["statement"] not in statements:
            errors.append(f"oracle: binding names unknown statement {b['statement']}")
        else:
            bound.setdefault(b["statement"], []).append(b)
    for sid, s in statements.items():
        label = f"oracle: {sid} ({s['kind']} {s['text']!r})"
        if s["kind"] == "part_count":
            if len(parts) != s["n"]:
                errors.append(f"{label}: plan has {len(parts)} parts, expected {s['n']}")
            continue
        if sid not in bound:
            errors.append(f"{label} unbound -- add an acceptance_bindings entry")
            continue
        for b in bound[sid]:
            if b["part"] == "*" and s["kind"] == "visual":
                continue
            part = parts.get(b["part"])
            if part is None:
                errors.append(f"{label}: bound part {b['part']!r} does not exist")
                continue
            by_name = {i.get("name"): i for i in part.get("interfaces") or []}
            labels = {p.get("label") for p in part.get("probes") or []}
            missing = [n for n in b.get("interfaces") or [] if n not in by_name]
            missing += [n for n in b.get("probes") or [] if n not in labels]
            if missing:
                errors.append(f"{label}: bound names {missing} not found on part {b['part']!r}")
                continue
            itfs = [by_name[n] for n in b.get("interfaces") or []]
            errors += [f"{label}: {e}" for e in _check_one(s, b, part, itfs, consts)]
    return errors


def visual_statements(doc: dict | None, plan: dict, part_id: str) -> list[dict]:
    """`visual` statements bound to `part_id` or to "*"."""
    if not doc:
        return []
    ids = {
        b["statement"] for b in plan.get("acceptance_bindings") or [] if b["part"] in (part_id, "*")
    }
    return [s for s in doc["statements"] if s["kind"] == "visual" and s["id"] in ids]


def _issue(s: dict, message: str) -> dict:
    return {
        "source": "oracle",
        "severity": "error",
        "type": "oracle_unmet",
        "statement": s["id"],
        "message": f"{s['id']} ({s['text']!r}): {message}",
        "hint": "Correct the part so it meets the statement (approved by the user at "
        "Phase 1). If the statement itself is wrong, escalate to the user.",
        "round": 1,
    }


def verify(
    plan: dict,
    doc: dict,
    part_id: str,
    body: Any,
    feature_issues: list[dict],
    consts: dict[str, float],
) -> list[dict]:
    """Gate issues for bound statements the built `body` (build pose) does not meet."""
    import probes

    part = next((p for p in plan.get("parts", []) if p["id"] == part_id), None)
    if part is None:
        return []
    statements = {s["id"]: s for s in doc["statements"]}
    failing_pos = {
        tuple(round(float(v), 2) for v in i["position_mm"])
        for i in feature_issues
        if i.get("part") == part_id
        and i.get("type") in ("feature_absent", "feature_drift")
        and i.get("position_mm")
    }
    by_name = {i.get("name"): i for i in part.get("interfaces") or []}
    issues = []
    for b in plan.get("acceptance_bindings") or []:
        s = statements.get(b["statement"])
        if s is None or b["part"] != part_id or s["kind"] in ("visual", "part_count"):
            continue
        if s["kind"] in ("feature", "fit", "spacing"):
            bad = [
                n
                for n in b.get("interfaces") or []
                if tuple(round(float(v), 2) for v in by_name.get(n, {}).get("position_mm", []))
                in failing_pos
            ]
            if bad:
                issues.append(_issue(s, f"bound interfaces {bad} were not built as declared"))
        elif s["kind"] == "extent":
            bb = body.BoundingBox()
            errs = _extent_errors(s, [bb.xlen, bb.ylen, bb.zlen], consts)
            if errs:
                issues.append(_issue(s, "; ".join(errs)))
        elif s["kind"] == "probe":
            for entry in _bound_probes(b, part):
                fields: dict[str, Any] = {
                    k: tuple(v) if isinstance(v, list) else v for k, v in entry.items()
                }
                fields.pop("instance", None)
                ok, got = probes.evaluate(probes.Probe(**fields), body)
                if not ok:
                    issues.append(_issue(s, f"probe {entry['label']!r} failed (got {got})"))
    return issues


def apply_rounds(issues: list[dict], previous: dict | None) -> None:
    """Set `round` from the previous gate report; `ask_user` from MAX_ROUNDS on (in place)."""
    prior = {
        i["statement"]: i.get("round", 1)
        for i in (previous or {}).get("issues", [])
        if i.get("type") == "oracle_unmet" and "statement" in i
    }
    for i in issues:
        if i.get("type") == "oracle_unmet":
            i["round"] = prior.get(i["statement"], 0) + 1
            i["action"] = "ask_user" if i["round"] >= MAX_ROUNDS else "fix"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate", help="Check acceptance.json (schema, ids, citations)")
    p.add_argument("acceptance", type=Path)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--intent", help="approved (or draft) intent text to check citations against")
    g.add_argument("--intent-file", type=Path, help="read the intent text from this file")
    g.add_argument("--plan", type=Path, help="read the intent from this BUILD_PLAN.json")
    p.add_argument(
        "--params",
        type=Path,
        default=Path("parameters.py"),
        help="parameters.py for expression names (skipped when absent)",
    )
    args = parser.parse_args(argv)

    try:
        doc = json.loads(args.acceptance.read_text(encoding="utf-8"))
        intent = args.intent
        if args.intent_file is not None:
            intent = args.intent_file.read_text(encoding="utf-8")
        if args.plan is not None:
            intent = json.loads(args.plan.read_text(encoding="utf-8")).get("intent")
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"success": False, "errors": [f"cannot read input: {exc}"]}))
        return 1
    consts = plan_params.load_constants(args.params) if args.params.is_file() else None
    errors = validate(doc, intent, consts)
    print(json.dumps({"success": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
