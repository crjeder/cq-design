#!/usr/bin/env python3
"""Per-script source history: every run's source, restorable by target.

``step_worker.py run`` and ``run_cadquery_model.py`` call ``record_run`` once per run, so
every distinct source a script was run with is kept as ``build/history/<stem>/<sha12>.py``
with ``run`` / ``mark`` / ``restore`` events in ``build/history/<stem>/log.jsonl``.

Usage:
    python3 script_history.py restore <target> build/plate.py
    python3 script_history.py mark <name> build/plate.py

Targets: ``@last_ok`` (latest successful, unsuppressed run), ``@prev`` (latest recorded
source differing from the current file), ``@<hash prefix>`` (4+ hex chars, unique), or a
mark name. Both commands print one JSON object; exit 0 on success, 1 otherwise.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SKIP_ENV = "CQ_HISTORY_SKIP"


def history_dir(script: Path) -> Path:
    return script.parent / "history" / script.stem


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _store(script: Path) -> str:
    """Write the script's current source as a blob (once); return its hash."""
    text = script.read_text(encoding="utf-8")
    sha = source_hash(text)
    blob = history_dir(script) / f"{sha}.py"
    if not blob.exists():
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_text(text, encoding="utf-8")
    return sha


def _events(script: Path) -> list[dict]:
    path = history_dir(script) / "log.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _append(script: Path, event: dict) -> None:
    path = history_dir(script) / "log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**event, "ts": time.time()}) + "\n")


def record_run(
    script: Path, ok: bool, *, attempt: int | None = None, suppressed: list | None = None
) -> None:
    """Record one run of script; never raises (history must not change a run's result)."""
    if os.environ.get(SKIP_ENV) == "1":
        return
    try:
        event: dict = {"event": "run", "src": _store(script), "ok": bool(ok)}
        if attempt is not None:
            event["attempt"] = attempt
        if suppressed:
            event["suppressed"] = list(suppressed)
        _append(script, event)
    except Exception as exc:
        print(f"[cq-design:history] run not recorded: {exc}", file=sys.stderr)


def _resolve(script: Path, target: str, events: list[dict]) -> tuple[str | None, str | None]:
    """(hash, None) for a target, or (None, error)."""
    with_src = [e for e in events if e.get("src")]
    if target == "@last_ok":
        runs = [e for e in with_src if e["event"] == "run" and e.get("ok")]
        runs = [e for e in runs if not e.get("suppressed")]
        return (runs[-1]["src"], None) if runs else (None, "no successful run recorded")
    if target == "@prev":
        current = source_hash(script.read_text(encoding="utf-8")) if script.exists() else None
        older = [e["src"] for e in with_src if e["src"] != current]
        return (older[-1], None) if older else (None, "no earlier source recorded")
    if target.startswith("@"):
        prefix = target[1:].lower()
        if len(prefix) < 4 or any(c not in "0123456789abcdef" for c in prefix):
            return None, f"{target!r}: a hash prefix needs at least 4 hex characters"
        found = sorted(p.stem for p in history_dir(script).glob(f"{prefix}*.py"))
        if len(found) == 1:
            return found[0], None
        if found:
            return None, f"{target!r} is ambiguous: {found}"
        return None, f"no recorded source matches {target!r}"
    marks = [e for e in with_src if e["event"] == "mark" and e.get("name") == target]
    return (marks[-1]["src"], None) if marks else (None, f"no mark {target!r}")


def current_attempt(script: Path) -> int | None:
    """The part's plan revision, or None when no project plan has a part named like script."""
    from log import load_project_plan, plan_revision

    plan = load_project_plan(script.parent)
    if not plan or not any(p.get("id") == script.stem for p in plan.get("parts", [])):
        return None
    return plan_revision(plan, script.stem)


def restore(script: Path, target: str) -> dict:
    """Rewrite script from the source target resolves to."""
    events = _events(script)
    sha, error = _resolve(script, target, events)
    if sha is None:
        return {"success": False, "target": target, "error": error}
    replaced = _store(script) if script.exists() else None
    blob = history_dir(script) / f"{sha}.py"
    script.write_text(blob.read_text(encoding="utf-8"), encoding="utf-8")
    _append(script, {"event": "restore", "target": target, "src": sha, "replaced": replaced})
    steps_log = script.parent / f"{script.stem}.steps.jsonl"
    if steps_log.exists():
        with steps_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "restore", "name": target, "ts": time.time()}) + "\n")
    result: dict = {"success": True, "target": target, "src": sha}
    runs = [e for e in events if e.get("event") == "run" and e.get("src") == sha]
    was = runs[-1].get("attempt") if runs else None
    now = current_attempt(script)
    if was is not None and now is not None and was != now:
        result["warning"] = "attempt_mismatch"
        result["attempts"] = {"source": was, "current": now}
    return result


def mark(script: Path, name: str) -> dict:
    """Record the script's current source under name."""
    if name.startswith("@"):
        return {"success": False, "error": f"mark names may not start with '@': {name!r}"}
    sha = _store(script)
    _append(script, {"event": "mark", "name": name, "src": sha})
    return {"success": True, "mark": name, "src": sha}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("action", choices=["restore", "mark"])
    ap.add_argument("name", help="restore target or mark name")
    ap.add_argument("script")
    args = ap.parse_args(argv)
    script = Path(args.script).resolve()
    if args.action == "mark" and not script.exists():
        result = {"success": False, "error": f"no script {args.script!r}"}
    else:
        result = (restore if args.action == "restore" else mark)(script, args.name)
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
