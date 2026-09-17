"""Append-only per-attempt telemetry log (build/attempts.jsonl).

One JSON line per part-script attempt, written by two paths:

    python telemetry.py append build/attempts.jsonl '{"part_id": ...}'
    python telemetry.py append build/attempts.jsonl --field part_id=housing \
        --field attempt=2 --field outcome=fail \
        --field 'error_types=["silent_boolean"]'

and a ``PostToolUse`` hook (wired by ``init_permissions.py``) that observes each
``run_cadquery_model.py`` Bash/PowerShell call and appends the base record itself:

    python telemetry.py --hook

A ``(part_id, attempt)`` pair may end up with more than one line (the hook's base
record, plus an audit-verdict follow-up appended by the orchestrator per
skill/phase3_build.md's Implementation audit) -- see ``fold_attempts``.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def record_attempt(attempts_log: Path, part_id: str, result: dict, model: str | None) -> None:
    """Append the base record for one run_cadquery_model.py result; skips stubs and
    records missing a required field (fail-open, like the hook)."""
    if part_id.endswith("_stub"):
        return
    existing = [r for r in _read_records(attempts_log) if r.get("part_id") == part_id]
    attempt = len(fold_attempts(existing)) + 1
    record: dict = {
        "part_id": part_id,
        "attempt": attempt,
        "outcome": "pass" if result.get("success") else "fail",
        "error_types": [
            e.get("type") for e in result.get("errors", []) if isinstance(e, dict) and e.get("type")
        ],
        "visual_review": None,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hook",
        action="store_true",
        help="read a PostToolUse payload from stdin; append a base record if applicable",
    )
    sub = parser.add_subparsers(dest="command")
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
    af = sub.add_parser("audit-fail", help="append a visual-review-failure follow-up record")
    af.add_argument("--part", required=True, help="part_id")
    af.add_argument("--audit", required=True, help="path to the auditor's JSON output")
    af.add_argument(
        "--file",
        default="build/attempts.jsonl",
        help="JSONL file to append to (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if args.hook:
        return _run_hook()
    if not args.command:
        parser.error("a command is required without --hook")

    if args.command == "audit-fail":
        try:
            audit_fail(args.file, args.part, args.audit)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(f"telemetry: {exc}", file=sys.stderr)
            return 1
        return 0

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
