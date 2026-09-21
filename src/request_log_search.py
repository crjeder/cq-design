#!/usr/bin/env python3
"""Search and append entries in a BUILD_PLAN.json's request_log.

Stdlib only (jsonschema is only imported by the `add` subcommand, which validates
against build_plan_schema.json before writing).

`search` filters request_log entries by a case-insensitive substring match on `text`
(--query), an exact `kind` match (--kind), an exact `level` match (--level), and/or a
`targets` membership substring (--target), printing only the entries matching every
supplied filter as JSON.

`add` appends one `clarification`/`correction` entry with `ts` set to the current UTC
time, validating the result against build_plan_schema.json before writing. `--reconciled`
also sets the plan's `intent_ts` to that `ts`; an unflagged `add` deliberately leaves the
plan failing plan_validate.py until `intent` is dealt with.

Usage:
    python request_log_search.py search BUILD_PLAN.json --query hinge
    python request_log_search.py search BUILD_PLAN.json --kind correction
    python request_log_search.py search BUILD_PLAN.json --level parameter --target cradle
    python request_log_search.py add BUILD_PLAN.json --kind correction \
        --text "widen the hinge pin hole" --level parameter --target cradle

Exit codes: 0 success (search: including no matches), 1 on error (missing file,
invalid JSON, failed schema validation).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "build_plan_schema.json")


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


def add_request_log_entry(
    plan: dict,
    *,
    kind: str,
    text: str,
    level: str | None = None,
    targets: list[str] | None = None,
    reconciled: bool = False,
) -> dict:
    """Return a new plan dict with one entry appended to request_log.

    Raises ValueError if kind is 'initial' or the resulting request_log fails
    schema validation. Does not mutate the input plan.
    """
    if kind == "initial":
        raise ValueError("add does not accept --kind initial (written once by the planner)")

    entry: dict = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "text": text,
    }
    if level is not None:
        entry["level"] = level
    if targets:
        entry["targets"] = targets

    new_plan = dict(plan)
    new_plan["request_log"] = [*(plan.get("request_log") or []), entry]
    if reconciled:
        new_plan["intent_ts"] = entry["ts"]

    import jsonschema

    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)
    problems = []
    for err in validator.iter_errors(new_plan):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        problems.append(f"Schema error at {path}: {err.message}")
    if problems:
        raise ValueError("; ".join(problems))

    return new_plan


def _cmd_search(args: argparse.Namespace) -> int:
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


def _cmd_add(args: argparse.Namespace) -> int:
    try:
        with open(args.plan, encoding="utf-8") as f:
            plan = json.load(f)
    except OSError as exc:
        print(f"request_log_search: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"request_log_search: invalid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        new_plan = add_request_log_entry(
            plan,
            kind=args.kind,
            text=args.text,
            level=args.level,
            targets=args.target,
            reconciled=args.reconciled,
        )
    except ValueError as exc:
        print(f"request_log_search: {exc}", file=sys.stderr)
        return 1

    with open(args.plan, "w", encoding="utf-8") as f:
        json.dump(new_plan, f, indent=2)
        f.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="filter request_log entries")
    sp.add_argument("plan", help="Path to BUILD_PLAN.json")
    sp.add_argument("--query", help="Case-insensitive substring match against entry text")
    sp.add_argument(
        "--kind",
        choices=["initial", "clarification", "correction"],
        help="Exact match against entry kind",
    )
    sp.add_argument(
        "--level",
        choices=["functional", "operation", "parameter"],
        help="Exact match against entry level",
    )
    sp.add_argument(
        "--target",
        help="Case-insensitive substring match against any string in entry targets",
    )
    sp.set_defaults(func=_cmd_search)

    ap = sub.add_parser("add", help="append one request_log entry")
    ap.add_argument("plan", help="Path to BUILD_PLAN.json")
    ap.add_argument(
        "--kind",
        required=True,
        choices=["initial", "clarification", "correction"],
        help="'initial' is rejected -- written once by the planner, not appended",
    )
    ap.add_argument("--text", required=True, help="the user's wording, verbatim")
    ap.add_argument("--level", choices=["functional", "operation", "parameter"])
    ap.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="NAME",
        help="a part id or part.feature/parameter name this entry affects (repeatable)",
    )
    ap.add_argument(
        "--reconciled",
        action="store_true",
        help="set intent_ts to this entry's ts; pass only after rewriting `intent` (or "
        "deciding no rewrite is needed). Without it the plan fails validation",
    )
    ap.set_defaults(func=_cmd_add)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
