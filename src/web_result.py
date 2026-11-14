"""Validate the JSON block a web-reading agent returns; emit typed data plus a display table."""

import argparse
import json
import re
import sys
import urllib.parse

PLATFORMS = ("github", "thingiverse", "printables", "makerworld", "other")
KINDS = ("cadquery", "build123d", "openscad", "freecad", "step", "brep", "iges", "mesh")
REUSABLE = (
    "yes",
    "no (none stated)",
    "no (ND)",
    "rung-3-only (ND, redistribution permitted)",
    "rung-3-only (ND, link only)",
)
RUNGS = ("1", "2", "3?", "4?", "n/a")
UNITS = ("mm", "g")
STATUSES = ("confirmed", "single-source", "conflict", "missing")
MAX_URL, MAX_ITEM, MAX_NOTES, MAX_LICENSE = 500, 120, 300, 120

_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def _clean(text: str) -> str:
    """Drop ANSI and control chars (newlines become spaces) and neutralize table pipes."""
    text = _ANSI.sub("", str(text))
    text = re.sub(r"[\r\n\t]+", " ", text)
    return _CTRL.sub("", text).replace("|", "/")


def _url_ok(url) -> bool:
    if not isinstance(url, str) or len(url) > MAX_URL or re.search(r"[\s\x00-\x1f\x7f]", url):
        return False
    p = urllib.parse.urlparse(url)
    return p.scheme in ("http", "https") and bool(p.netloc)


class _Errors(list):
    def add(self, where: str, message: str, hint: str, kind: str = "invalid_field") -> None:
        self.append({"type": kind, "message": f"{where}: {message}", "hint": hint})


def _enum(errs, where, rec, key, allowed):
    if rec.get(key) not in allowed:
        errs.add(
            f"{where}.{key}", f"{rec.get(key)!r} not allowed", f"one of {list(allowed)}", "bad_enum"
        )


def _text(errs, where, rec, key, limit, required=True):
    v = rec.get(key)
    if v is None and not required:
        return
    if not isinstance(v, str) or len(v) > limit:
        errs.add(
            f"{where}.{key}",
            f"must be a string of at most {limit} chars",
            f"shorten {key}",
            "bad_text",
        )


def _candidate(errs, i, rec):
    w = f"candidates[{i}]"
    if not _url_ok(rec.get("url")):
        errs.add(
            f"{w}.url",
            "not a clean http(s) URL",
            "single-line http(s) URL, <= 500 chars",
            "bad_url",
        )
    for key, allowed in (
        ("platform", PLATFORMS),
        ("kind", KINDS),
        ("reusable", REUSABLE),
        ("rung", RUNGS),
    ):
        _enum(errs, w, rec, key, allowed)
    _text(errs, w, rec, "license", MAX_LICENSE)
    _text(errs, w, rec, "notes", MAX_NOTES, required=False)


def _row(errs, i, rec):
    w = f"rows[{i}]"
    _text(errs, w, rec, "item", MAX_ITEM)
    _enum(errs, w, rec, "unit", UNITS)
    _enum(errs, w, rec, "status", STATUSES)
    v = rec.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        errs.add(
            f"{w}.value", f"{v!r} is not a number", "plain number, unit goes in `unit`", "bad_value"
        )
    elif v == -1 and rec.get("status") != "missing":
        errs.add(
            f"{w}.value", "-1 only allowed with status missing", "set status missing", "bad_value"
        )
    urls = rec.get("source_urls")
    if not isinstance(urls, list) or not all(_url_ok(u) for u in urls):
        errs.add(
            f"{w}.source_urls",
            "must be a list of clean http(s) URLs",
            "single-line http(s) URLs",
            "bad_url",
        )
    elif not urls and rec.get("status") != "missing":
        errs.add(
            f"{w}.source_urls",
            "empty list needs status missing",
            "cite a source or mark missing",
            "bad_url",
        )
    _text(errs, w, rec, "notes", MAX_NOTES, required=False)


_SHAPES = {
    "sourcing": (
        "candidates",
        _candidate,
        ("url", "platform", "kind", "license", "reusable", "rung"),
    ),
    "research": ("rows", _row, ("item", "value", "unit", "source_urls", "status")),
}


def _table(kind: str, records: list) -> str:
    if kind == "sourcing":
        head = ["Source", "Platform", "Kind", "License", "Reusable", "Rung", "Notes"]
        keys = ["url", "platform", "kind", "license", "reusable", "rung", "notes"]
    else:
        head = ["Item", "Value", "Unit", "Source", "Status", "Notes"]
        keys = ["item", "value", "unit", "source_urls", "status", "notes"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in records:
        cells = [
            ", ".join(map(str, r[k])) if isinstance(r.get(k), list) else r.get(k, "") for k in keys
        ]
        lines.append("| " + " | ".join(_clean(c) for c in cells) + " |")
    return "\n".join(lines)


def validate(kind: str, raw) -> dict:
    """Validate parsed JSON; return success, errors, data (no notes) and display_markdown."""
    key, check, required = _SHAPES[kind]
    errs = _Errors()
    records = raw.get(key) if isinstance(raw, dict) else None
    if not isinstance(records, list):
        errs.add(key, "missing or not a list", f'top level must be {{"{key}": [...]}}', "bad_shape")
        return {"success": False, "errors": list(errs), "data": {key: []}, "display_markdown": ""}
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errs.add(f"{key}[{i}]", "not an object", "one object per record", "bad_shape")
            continue
        for field in required:
            if field not in rec:
                errs.add(f"{key}[{i}].{field}", "missing", f"add {field}", "missing_field")
        check(errs, i, rec)
    if errs:
        return {"success": False, "errors": list(errs), "data": {key: []}, "display_markdown": ""}
    data = {key: [{k: v for k, v in r.items() if k in required} for r in records]}
    return {"success": True, "errors": [], "data": data, "display_markdown": _table(kind, records)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--kind", choices=sorted(_SHAPES), required=True)
    v.add_argument("file")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError) as e:
        result = {
            "success": False,
            "data": {},
            "display_markdown": "",
            "errors": [
                {"type": "bad_json", "message": str(e), "hint": "return one valid json block"}
            ],
        }
    else:
        result = validate(args.kind, raw)
    print(json.dumps(result))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
