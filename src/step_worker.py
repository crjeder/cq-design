#!/usr/bin/env python3
"""Warm step worker for step-form part scripts (builder-only).

The client starts one worker per build directory on demand (127.0.0.1, random port,
authkey; address in ``<build>/.step_worker.json``). The worker keeps CadQuery imported and
caches every step's result under a key chained over the previous steps (``blocks.Part``),
so a re-run executes only from the first changed step. It exits after an idle timeout.
If the worker dies or times out mid-run, the client kills it and runs the same request
cold in a subprocess (``"worker": "fallback"``).

Usage:
    python3 step_worker.py run build/plate.py [-- <run_cadquery_model.py args>]
    python3 step_worker.py snapshot save|restore <name> build/plate.py
    python3 step_worker.py snapshot compare <a> <b> build/plate.py

``run`` prints ``{success, part_id, steps, failed_step, failing_probes, diff_vs_last_good,
probe_stuck, stuck_occurrences, unprobed_interfaces, worker, full}``. ``full`` is the
``run_cadquery_model.py`` result, run only when every step passed. Probe failures are
logged to ``<build>/<part>.steps.jsonl``; a probe that fails again after a restore or after
the failing step's content changed sets ``probe_stuck``.
"""

import argparse
import contextlib
import hashlib
import json
import os
import runpy
import secrets
import subprocess
import sys
import threading
import time
import traceback
from multiprocessing.connection import Client, Listener
from pathlib import Path
from typing import Any, cast

SRC = Path(__file__).resolve().parent
IDLE_TIMEOUT_S = 600
RUN_TIMEOUT_S = 300
START_TIMEOUT_S = 60
ADDRESS_FILE = ".step_worker.json"

# Per-script step caches, alive for the worker's lifetime (cold runs start empty).
_CACHES: dict[str, dict] = {}


# --- execution (worker and cold) ----------------------------------------------------


def _summary(state: dict | None) -> dict | None:
    """Volume, bbox, solid and face count of a Part state's bodies."""
    if not state:
        return None
    import cadquery as cq

    bodies = [b for b in [state["body"], *state["unions"].values()] if b is not None]
    if not bodies:
        return None
    shape = bodies[0] if len(bodies) == 1 else cq.Compound.makeCompound(bodies)
    bb = shape.BoundingBox()
    return {
        "volume": round(shape.Volume(), 3),
        "bbox": [round(v, 3) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)],
        "solids": len(shape.Solids()),
        "faces": len(shape.Faces()),
    }


def _execute(script: Path, cache: dict | None) -> tuple[object, str | None]:
    """Run the script with Part caching. Returns (the script's Part, error text or None)."""
    from blocks import Part

    Part.cache, Part.last = cache, None
    old_cwd = os.getcwd()
    os.chdir(script.parent)
    try:
        runpy.run_path(str(script), run_name="__main__")
        return Part.last, None
    except Exception:
        return Part.last, traceback.format_exc(limit=3)
    finally:
        os.chdir(old_cwd)
        Part.cache = None


def _step_content(step: dict) -> str:
    """Hash of a step's own content (kind, entry, args), independent of earlier steps."""
    keep = {k: step.get(k) for k in ("kind", "block", "id", "args", "op", "at")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()


def _probe_id(probe: dict) -> list:
    loc = [round(v, 1) for v in probe["p"]] if probe.get("p") else None
    return [probe.get("owner"), probe.get("kind"), loc, probe.get("label")]


def _history(script: Path) -> Path:
    return script.parent / f"{script.stem}.steps.jsonl"


def _check_stuck(script: Path, failing: list[dict], content: str) -> list[dict]:
    """Earlier failures of the same probes after a restore or a changed step: stuck."""
    path = _history(script)
    events = []
    if path.exists():
        events = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        ]
    ids = [_probe_id(p) for p in failing]
    stuck, restored = [], False
    for ev in events:
        if ev.get("event") == "restore":
            restored = True
            continue
        if any(i in ev.get("probes", []) for i in ids) and (restored or ev["content"] != content):
            stuck.append(ev)
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({"event": "fail", "probes": ids, "content": content, "ts": time.time()})
            + "\n"
        )
    return stuck


def _log_run(script: Path, part_id: str, ok: bool) -> None:
    """Append this run to steps.jsonl under the part's current attempt (plan revision)."""
    from log import load_project_plan, plan_revision

    attempt = plan_revision(load_project_plan(script.parent), part_id)
    with _history(script).open("a", encoding="utf-8") as f:
        record = {"event": "run", "ok": ok, "attempt": attempt, "ts": time.time()}
        f.write(json.dumps(record) + "\n")


def run_steps(script: Path, cache: dict | None) -> dict:
    """Execute the step list and build the report (no full tier)."""
    part, error = _execute(script, cache)
    _log_run(script, getattr(part, "id", script.stem), error is None)
    steps = list(getattr(part, "steps", []))
    failed = next((s for s in steps if not s.get("ok", True)), None)
    report: dict = {
        "success": error is None,
        "part_id": getattr(part, "id", script.stem),
        "steps": steps,
        "failed_step": failed["index"] if failed else None,
        "failing_probes": [],
        "diff_vs_last_good": None,
        "probe_stuck": False,
        "unprobed_interfaces": getattr(part, "unprobed_interfaces", []),
    }
    if error is None:
        return report
    report["error"] = error.strip().splitlines()[-1]
    if failed is None or part is None:
        return report
    report["failing_probes"] = failed.get("probes", {}).get("failed", [])
    if failed["kind"] == "place":
        report["diff_vs_last_good"] = {
            "last_good": _summary(part.last_good),  # type: ignore[attr-defined]
            "failed": _summary(part._state()),  # type: ignore[attr-defined]
        }
    if report["failing_probes"]:
        stuck = _check_stuck(script, report["failing_probes"], _step_content(failed))
        report["probe_stuck"], report["stuck_occurrences"] = bool(stuck), stuck
    return report


def _snapshot_dir(script: Path) -> Path:
    return script.parent / "snapshots" / script.stem


def snapshot(action: str, names: list[str], script: Path, cache: dict | None) -> dict:
    """save/restore/compare builder-only snapshots of a script's last passing step."""
    import cadquery as cq

    import probes as pr

    d = _snapshot_dir(script)
    if action == "save":
        part, _ = _execute(script, cache)
        state = getattr(part, "last_good", None)
        if not state:
            return {"success": False, "error": "no passing place step to snapshot"}
        d.mkdir(parents=True, exist_ok=True)
        bodies = [b for b in [state["body"], *state["unions"].values()] if b is not None]
        cq.Compound.makeCompound(bodies).exportBrep(str(d / f"{names[0]}.brep"))
        (d / f"{names[0]}.py").write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
        probes = [pr.as_dict(p) for p in state["probes"]]
        (d / f"{names[0]}.registry.json").write_text(json.dumps(probes), encoding="utf-8")
        return {"success": True, "saved": names[0], "summary": _summary(state)}
    if action == "restore":
        src = d / f"{names[0]}.py"
        if not src.exists():
            return {"success": False, "error": f"no snapshot {names[0]!r}"}
        script.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        with _history(script).open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "restore", "name": names[0], "ts": time.time()}) + "\n")
        return {"success": True, "restored": names[0]}
    a, b = (cq.Shape.importBrep(str(d / f"{n}.brep")) for n in names)
    regs = [json.loads((d / f"{n}.registry.json").read_text(encoding="utf-8")) for n in names]
    seen = {json.dumps(p, sort_keys=True): p for reg in regs for p in reg}
    changed = []
    for p in seen.values():
        fields: dict[str, Any] = {k: tuple(v) if isinstance(v, list) else v for k, v in p.items()}
        probe = pr.Probe(**fields)
        states = [pr.evaluate(probe, s)[0] for s in (a, b)]
        if states[0] != states[1]:
            changed.append({**p, "states": dict(zip(names, states, strict=True))})

    def info(s):
        bb = s.BoundingBox()
        return {
            "volume": round(s.Volume(), 3),
            "solids": len(s.Solids()),
            "faces": len(s.Faces()),
            "bbox": [round(v, 3) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)],
        }

    return {"success": True, names[0]: info(a), names[1]: info(b), "probes_changed": changed}


def handle(request: dict, cache_for) -> dict:
    """Serve one request; cache_for(script) gives the step cache (None = cold)."""
    script = Path(request["script"]).resolve()
    if request["cmd"] == "run":
        return run_steps(script, cache_for(script))
    return snapshot(request["action"], request["names"], script, cache_for(script))


# --- server -------------------------------------------------------------------------


def serve(build_dir: Path) -> None:
    import cadquery  # noqa: F401  -- the point of the worker: import once

    os.environ["CQ_STEP_WORKER"] = "1"
    key = secrets.token_bytes(16)
    listener = Listener(("127.0.0.1", 0), authkey=key)
    host, port = cast(tuple[str, int], listener.address)
    (build_dir / ADDRESS_FILE).write_text(
        json.dumps({"host": host, "port": port, "authkey": key.hex(), "pid": os.getpid()}),
        encoding="utf-8",
    )
    last = [time.monotonic()]

    def idle_watch():
        while time.monotonic() - last[0] < IDLE_TIMEOUT_S:
            time.sleep(5)
        os._exit(0)

    threading.Thread(target=idle_watch, daemon=True).start()
    while True:
        with listener.accept() as conn:
            request = conn.recv()
            report = handle(request, lambda s: _CACHES.setdefault(str(s), {}))
            conn.send(report)
            last[0] = time.monotonic()


# --- client -------------------------------------------------------------------------


def _connect(build_dir: Path):
    try:
        info = json.loads((build_dir / ADDRESS_FILE).read_text(encoding="utf-8"))
        return Client((info["host"], info["port"]), authkey=bytes.fromhex(info["authkey"])), info
    except (OSError, ValueError, KeyError, EOFError):
        return None, None


def _start(build_dir: Path):
    (build_dir / ADDRESS_FILE).unlink(missing_ok=True)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "serve", str(build_dir)],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )
    deadline = time.monotonic() + START_TIMEOUT_S
    while time.monotonic() < deadline:
        conn, info = _connect(build_dir)
        if conn:
            return conn, info
        time.sleep(0.2)
    return None, None


def _kill(info: dict | None) -> None:
    if not info:
        return
    with contextlib.suppress(OSError, KeyError):
        os.kill(info["pid"], 9)


def _cold(request: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "cold", json.dumps(request)],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_S,
    )
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        report = {"success": False, "error": (proc.stderr or "cold run crashed").strip()[-500:]}
    return {**report, "worker": "fallback"}


def request_worker(request: dict) -> dict:
    """Send a request to the build dir's worker (starting it if needed); fall back cold."""
    build_dir = Path(request["script"]).resolve().parent
    conn, info = _connect(build_dir)
    if conn is None:
        conn, info = _start(build_dir)
    if conn is None:
        return _cold(request)
    try:
        with conn:
            conn.send(request)
            if conn.poll(RUN_TIMEOUT_S):
                return {**conn.recv(), "worker": "warm"}
    except (EOFError, OSError):
        pass
    _kill(info)
    (build_dir / ADDRESS_FILE).unlink(missing_ok=True)
    return _cold(request)


def _full_tier(script: Path, extra: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SRC / "run_cadquery_model.py"), str(script), *extra],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"success": False, "errors": [{"type": "wrapper_output", "message": proc.stderr}]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("script")
    r.add_argument("full_args", nargs="*", help="run_cadquery_model.py args (after --)")
    r.add_argument("--no-full", action="store_true", help="skip the full tier")
    s = sub.add_parser("snapshot")
    s.add_argument("action", choices=["save", "restore", "compare"])
    s.add_argument("names", nargs="+")
    sv = sub.add_parser("serve")
    sv.add_argument("build_dir")
    c = sub.add_parser("cold")
    c.add_argument("request")
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        serve(Path(args.build_dir))
        return 0
    if args.cmd == "cold":
        print(json.dumps(handle(json.loads(args.request), lambda s: None), default=str))
        return 0
    if args.cmd == "snapshot":
        n = 2 if args.action == "compare" else 1
        if len(args.names) != n + 1:
            ap.error(f"snapshot {args.action} takes {n} name(s) and the script")
        req = {
            "cmd": "snapshot",
            "action": args.action,
            "names": args.names[:n],
            "script": args.names[n],
        }
        report = request_worker(req)
    else:
        report = request_worker({"cmd": "run", "script": args.script})
        report["full"] = None
        if report.get("success") and not args.no_full:
            report["full"] = _full_tier(Path(args.script), args.full_args)
            report["success"] = bool(report["full"].get("success"))
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
