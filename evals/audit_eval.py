#!/usr/bin/env python3
"""Auditor eval: does the auditor catch seeded defects in an L-bracket and pass the good one?

`prepare` (no model calls) builds one part script per variant from `evals/cases/l-bracket`,
renders previews + sections, and renders the audit prompt. `--run MODEL` (opt-in, costs
tokens) then runs `claude -p --model MODEL` on each prompt and scores verdict vs expected.

    python evals/audit_eval.py --out runs/audit
    python evals/audit_eval.py --out runs/audit --run claude-sonnet-5-5 --run claude-opus-5-5
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CASE = ROOT / "evals/cases/l-bracket"

TEMPLATE = """import cadquery as cq

W = 60
D = 40
T = 6
UP_H = {up_h}
UP_Z0 = {up_z0}
HOLE_D = {hole_d}

base = cq.Workplane("XY").box(W, D, T, centered=(True, False, False))
upright = cq.Workplane("XY").box(W, T, UP_H, centered=(True, False, False)).translate((0, 0, UP_Z0))
result = base.union(upright)
if HOLE_D:
    cbore = cq.Workplane("XY").workplane(offset=T / 2).center(0, 25).circle(HOLE_D).extrude(T)
    through = cq.Workplane("XY").center(0, 25).circle(HOLE_D / 2).extrude(T)
    upright_hole = cq.Workplane("XZ").center(0, UP_Z0 + UP_H * 2 / 3).circle(HOLE_D / 2).extrude(-T)
    result = result.cut(cbore).cut(through).cut(upright_hole)
"""

# variant -> (template params, expected verdict)
VARIANTS: dict[str, tuple[dict[str, float], str]] = {
    "good": ({"up_h": 60, "up_z0": 0, "hole_d": 5}, "pass"),
    "detached_upright": ({"up_h": 60, "up_z0": 7.5, "hole_d": 5}, "fail"),
    "short_upright": ({"up_h": 30, "up_z0": 0, "hole_d": 5}, "fail"),
    "missing_hole": ({"up_h": 60, "up_z0": 0, "hole_d": 0}, "fail"),
}


def _py(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, check=False)


def prepare(out: Path) -> dict[str, dict]:
    """Write scripts, previews and audit prompts per variant; return variant -> record."""
    plan_path = out / "BUILD_PLAN.json"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CASE / "BUILD_PLAN.json", plan_path)
    records = {}
    for name, (params, expected) in VARIANTS.items():
        d = out / name
        d.mkdir(exist_ok=True)
        script = d / "l_bracket.py"
        script.write_text(TEMPLATE.format(**params), encoding="utf-8")
        run = _py(
            str(SRC / "run_cadquery_model.py"), str(script), "--preview", "--cross-sections",
            "--extra-section", "x=0", "--extra-section", "y=3", "--preview-dir", str(d),
        )  # fmt: skip
        try:
            res = json.loads(run.stdout)
        except json.JSONDecodeError as e:
            raise SystemExit(f"{name}: unparseable run output\n{run.stdout}\n{run.stderr}") from e
        if not res.get("success"):
            raise SystemExit(f"{name}: build failed: {res.get('errors')}")
        previews = res.get("previews") or [res["preview"]]
        prompt = d / "audit_prompt.txt"
        r = _py(
            str(SRC / "render_prompt.py"), "audit", "--plan", str(plan_path), "--part",
            "l_bracket", "--script", str(script), "--previews", *previews, "--out", str(prompt),
        )  # fmt: skip
        if r.returncode:
            raise SystemExit(f"{name}: render_prompt failed\n{r.stderr}")
        records[name] = {"expected": expected, "prompt": prompt.as_posix()}
    (out / "variants.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records


def extract_verdict(text: str) -> dict | None:
    """Last JSON object in the auditor's final message that carries a `verdict`."""
    dec = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "verdict" in obj:
                found = obj
    return found


def run_auditor(model: str, rec: dict, cwd: Path, timeout: int) -> dict:
    prompt = f"Read {rec['prompt']} in full and follow it. Working directory: {cwd}."
    cmd = [
        "claude", "-p", prompt, "--model", model, "--output-format", "json",
        "--permission-mode", "acceptEdits", "--allowedTools", "Read", "Glob", "Grep", "Bash",
    ]  # fmt: skip
    proc = subprocess.run(
        cmd, cwd=cwd, timeout=timeout, check=False, capture_output=True, text=True
    )
    env = json.loads(proc.stdout)
    verdict = extract_verdict(str(env.get("result")))
    return {
        "verdict": verdict and verdict.get("verdict"),
        "failed": verdict and verdict.get("failed_questions"),
        "cost_usd": env.get("total_cost_usd"),
        "is_error": env.get("is_error"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Auditor eval on seeded L-bracket defects")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--run", action="append", default=[], metavar="MODEL")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()
    out = args.out.resolve()
    records = prepare(out)
    rows = []
    for model in args.run:
        for name, rec in records.items():
            got = run_auditor(model, rec, out, args.timeout)
            rows.append({"model": model, "variant": name, "expected": rec["expected"], **got})
            ok = "OK " if got["verdict"] == rec["expected"] else "BAD"
            print(f"{ok} {model} {name}: expected {rec['expected']}, got {got['verdict']}")
    if rows:
        (out / "audit_scores.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
