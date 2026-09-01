#!/usr/bin/env python3
"""Search a BUILD_PLAN.json's request_log without reading the whole array.

Stdlib only. Filters request_log entries by a case-insensitive substring
match on `text` (--query), an exact `kind` match (--kind), an exact `level`
match (--level), and/or a `targets` membership substring (--target), printing
only the entries matching every supplied filter as JSON.

Usage:
    python request_log_search.py BUILD_PLAN.json --query hinge
    python request_log_search.py BUILD_PLAN.json --kind correction
    python request_log_search.py BUILD_PLAN.json --level parameter --target cradle

Exit codes: 0 success (including no matches), 1 on error (missing file,
invalid JSON).
"""

from __future__ import annotations

import argparse
import json
import sys


def search_request_log(
    plan: dict,
    *,
    query: str | None = None,
    kind: str | None = None,
    level: str | None = None,
    target: str | None = None,
) -> list[dict]:
    """Return request_log entries matching every supplied filter.

    query: case-insensitive substring on `text`.
    kind/level: exact match (an entry with no `level` never matches `--level`).
    target: case-insensitive substring against any string in the entry's
    `targets` array (an entry with no `targets` never matches).
    """
    results = plan.get("request_log") or []
    if query is not None:
        needle = query.lower()
        results = [e for e in results if needle in e.get("text", "").lower()]
    if kind is not None:
        results = [e for e in results if e.get("kind") == kind]
    if level is not None:
        results = [e for e in results if e.get("level") == level]
    if target is not None:
        needle = target.lower()
        results = [e for e in results if any(needle in t.lower() for t in e.get("targets") or [])]
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="Path to BUILD_PLAN.json")
    parser.add_argument("--query", help="Case-insensitive substring match against entry text")
    parser.add_argument(
        "--kind",
        choices=["initial", "clarification", "correction"],
        help="Exact match against entry kind",
    )
    parser.add_argument(
        "--level",
        choices=["functional", "operation", "parameter"],
        help="Exact match against entry level",
    )
    parser.add_argument(
        "--target",
        help="Case-insensitive substring match against any string in entry targets",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.plan, encoding="utf-8") as f:
            plan = json.load(f)
    except OSError as exc:
        print(f"request_log_search: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"request_log_search: invalid JSON: {exc}", file=sys.stderr)
        return 1

    results = search_request_log(
        plan, query=args.query, kind=args.kind, level=args.level, target=args.target
    )
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
