#!/usr/bin/env python3
"""Append-or-search the pipeline's build-time logs: the milestone journal, the
per-attempt telemetry log, and a plan's request_log.

    python log.py journal append build/journal.md phase3/part_accepted:lid "audit passed"
    python log.py attempt append build/attempts.jsonl '{"part_id": ...}'
    python log.py attempt append build/attempts.jsonl --field part_id=housing \
        --field attempt=2 --field outcome=fail
    python log.py attempt audit-fail --part lid --audit build/lid_audit.json
    python log.py request search BUILD_PLAN.json --query hinge
    python log.py request add BUILD_PLAN.json --kind correction \
        --text "widen the hinge pin hole" --level parameter --target cradle

An attempt is a plan revision of a part (attempt 1 = the initial plan, +1 per
`request_log` entry targeting it); step-worker runs inside it are counted as
`step_runs` from ``build/<part>.steps.jsonl``, not as attempts.

`--hook` (no subcommand) is the ``PostToolUse`` hook entry point wired by
``init_permissions.py``: it observes each ``run_cadquery_model.py`` call and appends
the base attempt record itself.

See skill/resume.md for the journal's format and resume contract. Stdlib only
(jsonschema is imported only by `request add`, which validates against
build_plan_schema.json before writing).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def append_line(path: str | Path, milestone: str, text: str) -> str:
    """Append `- <milestone>: <text>` to path (created if absent). Returns the line."""
    line = f"- {milestone}: {text}"
    path = Path(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


SKILL_DIR = Path(__file__).resolve().parent.parent

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
    if "step_runs" in record and (
        not isinstance(record["step_runs"], int) or isinstance(record["step_runs"], bool)
    ):
        problems.append("field 'step_runs' must be int")
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


def fold_attempts(records: list[dict]) -> list[dict]:
    """Group records by (part_id, attempt); return one per group -- the last
    record in input order -- preserving each group's first-appearance order."""
    groups: dict[tuple, dict] = {}
    for rec in records:
        groups[(rec.get("part_id"), rec.get("attempt"))] = rec
    return list(groups.values())


def _read_records(path: Path) -> list[dict]:
    """Parseable JSON lines from path, or [] if the file is absent/empty/malformed."""
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


_RUN_MODEL_RE = re.compile(r"run_cadquery_model\.py")
_SCRIPT_ARG_RE = re.compile(r"build[/\\]([\w-]+)\.py")


def _model_from_transcript(transcript_path: str | None) -> str | None:
    """The model of the last assistant turn in the session transcript, if any."""
    if not transcript_path:
        return None
    path = Path(transcript_path)
    if not path.is_file():
        return None
    model = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        msg = obj.get("message")
        if isinstance(msg, dict) and msg.get("model"):
            model = msg["model"]
    return model


def _run_hook() -> int:
    """PostToolUse-hook entry point: derive and append a base attempt record from a
    run_cadquery_model.py Bash/PowerShell call. Fail-open: any problem (unmatched
    command, missing build/, unparseable result, invalid record) exits 0 and
    writes nothing -- a telemetry hook must never break a turn."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        if payload.get("tool_name") not in ("Bash", "PowerShell"):
            return 0
        command = payload.get("tool_input", {}).get("command", "")
        if not _RUN_MODEL_RE.search(command) or "--attempts-log" in command:
            return 0
        match = _SCRIPT_ARG_RE.search(command)
        if not match:
            return 0
        build_dir = Path(payload.get("cwd", ".")) / "build"
        if not build_dir.is_dir():
            return 0
        result = json.loads(payload.get("tool_response", {}).get("stdout", ""))
        model = _model_from_transcript(payload.get("transcript_path"))
        record_attempt(build_dir / "attempts.jsonl", match.group(1), result, model)
    except Exception:
        pass
    return 0


def part_author_model() -> str:
    """`models.part_author` from ./skill_config.json, else the seeded default."""
    for path in (Path("skill_config.json"), SKILL_DIR / "src/skill_config.default.json"):
        if path.is_file():
            model = (
                json.loads(path.read_text(encoding="utf-8")).get("models", {}).get("part_author")
            )
            if model and model != "inline":
                return model
    return "unknown"


def _prompt_chars(build_dir: Path, part_id: str, attempt: int) -> int | None:
    """Length of the attempt's rendered prompt file, if one exists on disk."""
    for name in (f"{part_id}_prompt_attempt{attempt}.txt", f"{part_id}_prompt.txt"):
        prompt_path = build_dir / name
        if prompt_path.is_file():
            return len(prompt_path.read_text(encoding="utf-8"))
    return None


def plan_revision(plan: dict | None, part_id: str) -> int:
    """Attempt number for part_id: 1 + the non-initial request_log entries that target it
    (by part id or `part.feature`); an entry with no `targets` revises every part."""
    revisions = 0
    for entry in (plan or {}).get("request_log", []):
        if entry.get("kind") == "initial":
            continue
        targets = entry.get("targets")
        if not targets or any(t == part_id or t.startswith(f"{part_id}.") for t in targets):
            revisions += 1
    return 1 + revisions


def load_project_plan(build_dir: Path) -> dict | None:
    """The project's BUILD_PLAN.json next to build/, or None."""
    path = build_dir.parent / "BUILD_PLAN.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def step_runs(build_dir: Path, part_id: str, attempt: int) -> int:
    """Step-worker runs of part_id logged in its steps.jsonl during this attempt."""
    events = _read_records(build_dir / f"{part_id}.steps.jsonl")
    return sum(1 for e in events if e.get("event") == "run" and e.get("attempt") == attempt)


def record_attempt(attempts_log: Path, part_id: str, result: dict, model: str | None) -> None:
    """Append the base record for one run_cadquery_model.py result; skips stubs and
    records missing a required field (fail-open, like the hook)."""
    if part_id.endswith("_stub"):
        return
    build_dir = attempts_log.parent
    attempt = plan_revision(load_project_plan(build_dir), part_id)
    record: dict = {
        "part_id": part_id,
        "attempt": attempt,
        "outcome": "pass" if result.get("success") else "fail",
        "error_types": [
            e.get("type") for e in result.get("errors", []) if isinstance(e, dict) and e.get("type")
        ],
        "visual_review": None,
        "step_runs": step_runs(build_dir, part_id, attempt),
    }
    if model:
        record["model"] = model
    prompt_chars = _prompt_chars(attempts_log.parent, part_id, attempt)
    if prompt_chars is not None:
        record["prompt_chars"] = prompt_chars
    if not validate_attempt(record):
        append_attempt(attempts_log, record)


def audit_fail(attempts_log: str | Path, part_id: str, audit_path: str | Path) -> dict:
    """Append the visual-review-failure follow-up record for part_id's latest attempt,
    deriving prompt_chars and model from disk. Raises ValueError if there is no prior
    attempt for part_id, or the audit JSON has no failed_questions."""
    attempts_log = Path(attempts_log)
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    failed_questions = audit.get("failed_questions") or []
    if not failed_questions:
        raise ValueError(f"audit at {audit_path} has no failed_questions")
    existing = fold_attempts(
        [r for r in _read_records(attempts_log) if r.get("part_id") == part_id]
    )
    if not existing:
        raise ValueError(f"no prior attempt for part_id {part_id!r} in {attempts_log}")
    attempt = max(r["attempt"] for r in existing)
    record: dict = {
        "part_id": part_id,
        "attempt": attempt,
        "outcome": "fail",
        "error_types": ["visual_mismatch"],
        "visual_review": {"passed": False, "failed_question": failed_questions[0]},
        "model": part_author_model(),
    }
    prompt_chars = _prompt_chars(attempts_log.parent, part_id, attempt)
    if prompt_chars is not None:
        record["prompt_chars"] = prompt_chars
    return append_attempt(attempts_log, record)


def _parse_field(spec: str) -> tuple[str, object]:
    key, sep, raw = spec.partition("=")
    if not sep or not key:
        raise ValueError(f"--field expects k=v, got {spec!r}")
    try:
        return key, json.loads(raw)
    except json.JSONDecodeError:
        return key, raw


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
    snapshot_dir: str | Path | None = None,
) -> dict:
    """Return a new plan dict with one entry appended to request_log.

    Raises ValueError if kind is 'initial' or the resulting request_log fails
    schema validation. Does not mutate the input plan. `snapshot_dir` stores
    `script_baseline` (part id -> script hash) on a `parameter`-level entry only.
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
    if snapshot_dir is not None and level == "parameter":
        from freshness import script_hash

        entry["script_baseline"] = {
            p.stem: script_hash(str(p)) for p in Path(snapshot_dir).glob("*.py")
        }

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
        print(f"request: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"request: invalid JSON: {exc}", file=sys.stderr)
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
        print(f"request: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"request: invalid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        new_plan = add_request_log_entry(
            plan,
            kind=args.kind,
            text=args.text,
            level=args.level,
            targets=args.target,
            reconciled=args.reconciled,
            snapshot_dir=args.snapshot_scripts,
        )
    except ValueError as exc:
        print(f"request: {exc}", file=sys.stderr)
        return 1

    with open(args.plan, "w", encoding="utf-8") as f:
        json.dump(new_plan, f, indent=2)
        f.write("\n")
    return 0


def _cmd_journal_append(args: argparse.Namespace) -> int:
    try:
        append_line(args.journal, args.milestone, args.text)
    except OSError as exc:
        print(f"journal: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_attempt_append(args: argparse.Namespace) -> int:
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


def _cmd_attempt_audit_fail(args: argparse.Namespace) -> int:
    try:
        audit_fail(args.file, args.part, args.audit)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"telemetry: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hook",
        action="store_true",
        help="read a PostToolUse payload from stdin; append a base attempt record if applicable",
    )
    sub = parser.add_subparsers(dest="group")

    journal = sub.add_parser("journal", help="build/journal.md milestone log")
    jsub = journal.add_subparsers(dest="command", required=True)
    ja = jsub.add_parser("append", help="append one milestone line")
    ja.add_argument("journal", help="path to journal.md (e.g. build/journal.md)")
    ja.add_argument("milestone", help="<phase>/<milestone_key>, e.g. phase3/part_accepted:lid")
    ja.add_argument("text", help="the fact being recorded, one line")
    ja.set_defaults(func=_cmd_journal_append)

    attempt = sub.add_parser("attempt", help="build/attempts.jsonl per-attempt telemetry")
    asub = attempt.add_subparsers(dest="command", required=True)
    aa = asub.add_parser("append", help="append one attempt record")
    aa.add_argument("file", help="JSONL file to append to (e.g. build/attempts.jsonl)")
    aa.add_argument("json", nargs="?", help="record as a JSON object")
    aa.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="K=V",
        help="set/override one field (value parsed as JSON, else string)",
    )
    aa.set_defaults(func=_cmd_attempt_append)
    af = asub.add_parser("audit-fail", help="append a visual-review-failure follow-up record")
    af.add_argument("--part", required=True, help="part_id")
    af.add_argument("--audit", required=True, help="path to the auditor's JSON output")
    af.add_argument(
        "--file",
        default="build/attempts.jsonl",
        help="JSONL file to append to (default: %(default)s)",
    )
    af.set_defaults(func=_cmd_attempt_audit_fail)

    request = sub.add_parser("request", help="BUILD_PLAN.json request_log")
    rsub = request.add_subparsers(dest="command", required=True)
    rs = rsub.add_parser("search", help="filter request_log entries")
    rs.add_argument("plan", help="Path to BUILD_PLAN.json")
    rs.add_argument("--query", help="Case-insensitive substring match against entry text")
    rs.add_argument(
        "--kind",
        choices=["initial", "clarification", "correction"],
        help="Exact match against entry kind",
    )
    rs.add_argument(
        "--level",
        choices=["functional", "operation", "parameter"],
        help="Exact match against entry level",
    )
    rs.add_argument(
        "--target",
        help="Case-insensitive substring match against any string in entry targets",
    )
    rs.set_defaults(func=_cmd_search)
    ra = rsub.add_parser("add", help="append one request_log entry")
    ra.add_argument("plan", help="Path to BUILD_PLAN.json")
    ra.add_argument(
        "--kind",
        required=True,
        choices=["initial", "clarification", "correction"],
        help="'initial' is rejected -- written once by the planner, not appended",
    )
    ra.add_argument("--text", required=True, help="the user's wording, verbatim")
    ra.add_argument("--level", choices=["functional", "operation", "parameter"])
    ra.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="NAME",
        help="a part id or part.feature/parameter name this entry affects (repeatable)",
    )
    ra.add_argument(
        "--reconciled",
        action="store_true",
        help="set intent_ts to this entry's ts; pass only after rewriting `intent` (or "
        "deciding no rewrite is needed). Without it the plan fails validation",
    )
    ra.add_argument(
        "--snapshot-scripts",
        metavar="DIR",
        help="with --level parameter: hash every DIR/<part>.py into the entry's "
        "script_baseline so quality_gate can flag edits outside --target",
    )
    ra.set_defaults(func=_cmd_add)

    args = parser.parse_args(argv)

    if args.hook:
        return _run_hook()
    if not getattr(args, "func", None):
        parser.error("a command is required without --hook")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
