#!/usr/bin/env python3
"""Search a BUILD_PLAN.json's request_log without reading the whole array.

Stdlib only. Filters request_log entries by a case-insensitive substring
match on `text` (--query) and/or an exact `kind` match (--kind), printing
only the matching entries as JSON.

Usage:
    python request_log_search.py BUILD_PLAN.json --query hinge
    python request_log_search.py BUILD_PLAN.json --kind correction

Exit codes: 0 success (including no matches), 1 on error (missing file,
invalid JSON).
"""

from __future__ import annotations

import argparse
import json
import sys


def search_request_log(
    plan: dict, *, query: str | None = None, kind: str | None = None
) -> list[dict]:
    """Return request_log entries matching query (substring on text) and/or kind."""
    entries = plan.get("request_log") or []
    results = entries
    if query is not None:
        needle = query.lower()
        results = [e for e in results if needle in e.get("text", "").lower()]
    if kind is not None:
        results = [e for e in results if e.get("kind") == kind]
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

    results = search_request_log(plan, query=args.query, kind=args.kind)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
