"""Append-only per-attempt telemetry log (build/attempts.jsonl).

One JSON line per part-script attempt. The orchestrating Claude is the single
writer; it calls the CLI after each attempt:

    python telemetry.py append build/attempts.jsonl '{"part_id": ...}'
    python telemetry.py append build/attempts.jsonl --field part_id=housing \
        --field attempt=2 --field outcome=fail \
        --field 'error_types=["silent_boolean"]'

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REQUIRED_FIELDS = {
    "part_id": str,
    "attempt": int,
    "outcome": str,
    "error_types": list,
    "prompt_chars": int,
    "model": str,
}
_OUTCOMES = {"pass", "fail"}


def validate_attempt(record: dict) -> list[str]:
    """Return a list of validation problems; empty means the record is valid."""
    problems = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    for field, typ in _REQUIRED_FIELDS.items():
        if field not in record:
            problems.append(f"missing required field '{field}'")
        elif not isinstance(record[field], typ) or isinstance(record[field], bool):
            problems.append(f"field '{field}' must be {typ.__name__}")
    if isinstance(record.get("outcome"), str) and record["outcome"] not in _OUTCOMES:
        problems.append(f"field 'outcome' must be one of {sorted(_OUTCOMES)}")
    if isinstance(record.get("attempt"), int) and record["attempt"] < 1:
        problems.append("field 'attempt' must be >= 1")
    if isinstance(record.get("error_types"), list) and not all(
        isinstance(e, str) for e in record["error_types"]
    ):
        problems.append("field 'error_types' must contain only strings")
    if "visual_review" not in record:
        problems.append("missing required field 'visual_review' (object or null)")
    elif record["visual_review"] is not None:
        vr = record["visual_review"]
        if not isinstance(vr, dict) or "passed" not in vr:
            problems.append("field 'visual_review' must be null or an object with 'passed'")
    return problems


def append_attempt(path: str | Path, record: dict) -> dict:
    """Validate, stamp ts when absent, and append one JSON line. Returns the record."""
    problems = validate_attempt(record)
    if problems:
        raise ValueError("; ".join(problems))
    record = dict(record)
    record.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return record


def _parse_field(spec: str) -> tuple[str, object]:
    key, sep, raw = spec.partition("=")
    if not sep or not key:
        raise ValueError(f"--field expects k=v, got {spec!r}")
    try:
        return key, json.loads(raw)
    except json.JSONDecodeError:
        return key, raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ap = sub.add_parser("append", help="append one attempt record")
    ap.add_argument("file", help="JSONL file to append to (e.g. build/attempts.jsonl)")
    ap.add_argument("json", nargs="?", help="record as a JSON object")
    ap.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="K=V",
        help="set/override one field (value parsed as JSON, else string)",
    )
    args = parser.parse_args(argv)

    record: dict = {}
    if args.json:
        try:
            record = json.loads(args.json)
        except json.JSONDecodeError as exc:
            print(f"telemetry: invalid JSON: {exc}", file=sys.stderr)
            return 1
    try:
        for spec in args.field:
            key, value = _parse_field(spec)
            record[key] = value
        record.setdefault("visual_review", None)
        append_attempt(args.file, record)
    except ValueError as exc:
        print(f"telemetry: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
