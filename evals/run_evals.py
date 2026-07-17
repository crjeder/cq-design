"""Eval runner for the cq-design canonical corpus.

Score mode (default, never invokes a model): reads a run directory holding one
subdirectory per case -- each with the run's `build/attempts.jsonl` telemetry
and produced per-part STLs -- and scores it against `evals/cases/`:

    uv run python evals/run_evals.py --run-dir <dir> [--cases a,b]

Generation (opt-in, costs real tokens): runs `claude -p` once per case in a
temp working directory, then scores the result:

    uv run python evals/run_evals.py --run-dir <dir> --generate [--cases a,b]

Metrics per case and aggregated: first-shot success rate, mean attempts-to-
pass, symmetric Chamfer distance (mm) against the golden meshes (bbox-center
aligned, no rotation solving), and estimated cost per accepted part from
telemetry prompt sizes and `model_prices.json`.

Scorecard is written as `scorecard.json` and `scorecard.md` in the run dir.
Dependencies: trimesh, numpy, rtree (all project deps).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

EVALS_DIR = Path(__file__).parent
CASES_DIR = EVALS_DIR / "cases"
PRICES_PATH = EVALS_DIR / "model_prices.json"
CHAMFER_SAMPLES = 2000
CHARS_PER_TOKEN = 4


def load_prices(path: Path = PRICES_PATH) -> dict:
    prices = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in prices.items() if not k.startswith("_")}


def read_attempts(case_run_dir: Path) -> list[dict] | None:
    """Attempt records for one case's run, or None when telemetry is missing."""
    log = case_run_dir / "build" / "attempts.jsonl"
    if not log.is_file():
        return None
    records = []
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def chamfer_mm(produced: trimesh.Trimesh, golden: trimesh.Trimesh) -> float:
    """Symmetric Chamfer distance in mm, both meshes centered by bbox center.

    Sampled points on each mesh are measured against the OTHER mesh's surface
    (point-to-surface, not point-to-point), so identical geometry scores 0
    regardless of sampling density.
    """

    def centered(mesh):
        mesh = mesh.copy()
        mesh.apply_translation(-(mesh.bounds[0] + mesh.bounds[1]) / 2.0)
        return mesh

    produced, golden = centered(produced), centered(golden)

    def one_way(src, dst):
        pts = trimesh.sample.sample_surface(src, CHAMFER_SAMPLES)[0]
        _, dists, _ = trimesh.proximity.closest_point(dst, np.asarray(pts))
        return float(np.mean(dists))

    return (one_way(produced, golden) + one_way(golden, produced)) / 2.0


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path)
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"{path} did not load as a single mesh")
    return mesh


def find_produced_stl(case_run_dir: Path, part_id: str) -> Path | None:
    direct = case_run_dir / "stl" / f"{part_id}.stl"
    if direct.is_file():
        return direct
    hits = [p for p in case_run_dir.rglob(f"{part_id}.stl") if "golden" not in p.parts]
    return hits[0] if hits else None


def attempt_metrics(attempts: list[dict] | None, prices: dict) -> dict:
    """First-shot rate, attempts-to-pass, and cost from one case's telemetry."""
    if attempts is None:
        return {
            "first_shot_rate": None,
            "mean_attempts_to_pass": None,
            "cost_per_accepted_part_usd": None,
            "telemetry": "unavailable",
        }
    parts: dict[str, list[dict]] = {}
    for rec in attempts:
        parts.setdefault(rec["part_id"], []).append(rec)

    first_shot = 0
    attempts_to_pass = []
    unpassed = []
    total_cost = 0.0
    accepted = 0
    for part_id, recs in parts.items():
        recs.sort(key=lambda r: r["attempt"])
        if any(r["attempt"] == 1 and r["outcome"] == "pass" for r in recs):
            first_shot += 1
        passing = [r["attempt"] for r in recs if r["outcome"] == "pass"]
        if passing:
            accepted += 1
            attempts_to_pass.append(min(passing))
        else:
            unpassed.append(part_id)
            attempts_to_pass.append(max(r["attempt"] for r in recs) + 1)
        for r in recs:
            rate = prices.get(r.get("model", "default"), prices["default"])
            total_cost += (r["prompt_chars"] / CHARS_PER_TOKEN) * rate / 1e6

    n = len(parts)
    return {
        "first_shot_rate": first_shot / n if n else None,
        "mean_attempts_to_pass": sum(attempts_to_pass) / n if n else None,
        "unpassed_parts": unpassed,
        "cost_per_accepted_part_usd": total_cost / accepted if accepted else None,
        "total_cost_usd": total_cost,
        "telemetry": "ok",
    }


def score_case(case: str, run_dir: Path, prices: dict) -> dict:
    case_dir = CASES_DIR / case
    plan = json.loads((case_dir / "BUILD_PLAN.json").read_text(encoding="utf-8"))
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    case_run_dir = run_dir / case

    result = {"case": case, **attempt_metrics(read_attempts(case_run_dir), prices)}

    chamfers: dict[str, float | None] = {}
    for part in plan["parts"]:
        part_id = part["id"]
        produced = find_produced_stl(case_run_dir, part_id)
        if produced is None:
            chamfers[part_id] = None
            continue
        golden = load_mesh(case_dir / "golden" / f"{part_id}.stl")
        chamfers[part_id] = chamfer_mm(load_mesh(produced), golden)
    measured = [c for c in chamfers.values() if c is not None]
    result["chamfer_mm"] = chamfers
    result["mean_chamfer_mm"] = sum(measured) / len(measured) if measured else None
    result["within_tolerance"] = (
        all(c <= meta["tolerance_mm"] for c in measured) if measured else None
    )
    return result


def aggregate(case_results: list[dict]) -> dict:
    def mean_of(key):
        vals = [r[key] for r in case_results if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "cases_scored": len(case_results),
        "first_shot_rate": mean_of("first_shot_rate"),
        "mean_attempts_to_pass": mean_of("mean_attempts_to_pass"),
        "mean_chamfer_mm": mean_of("mean_chamfer_mm"),
        "cost_per_accepted_part_usd": mean_of("cost_per_accepted_part_usd"),
    }


def _fmt(value, digits=3) -> str:
    return "unavailable" if value is None else f"{value:.{digits}f}"


def render_markdown(scorecard: dict) -> str:
    lines = [
        "# Eval scorecard",
        "",
        "Cost figures are estimates (tokens ~ prompt_chars / 4).",
        "",
        "| case | first-shot | attempts-to-pass | chamfer (mm) | cost/part (USD) |",
        "|---|---|---|---|---|",
    ]
    for r in scorecard["cases"]:
        lines.append(
            f"| {r['case']} | {_fmt(r['first_shot_rate'], 2)} "
            f"| {_fmt(r['mean_attempts_to_pass'], 2)} "
            f"| {_fmt(r['mean_chamfer_mm'])} "
            f"| {_fmt(r['cost_per_accepted_part_usd'], 4)} |"
        )
    agg = scorecard["aggregate"]
    lines += [
        "",
        f"**Aggregate** ({agg['cases_scored']} cases): "
        f"first-shot {_fmt(agg['first_shot_rate'], 2)}, "
        f"attempts-to-pass {_fmt(agg['mean_attempts_to_pass'], 2)}, "
        f"chamfer {_fmt(agg['mean_chamfer_mm'])} mm, "
        f"cost/part {_fmt(agg['cost_per_accepted_part_usd'], 4)} USD",
        "",
    ]
    return "\n".join(lines)


def generate_case(case: str, run_dir: Path, timeout_s: int) -> None:
    """Run `claude -p` for one case in its own working directory (costs tokens)."""
    case_run_dir = run_dir / case
    case_run_dir.mkdir(parents=True, exist_ok=True)
    request = (CASES_DIR / case / "request.md").read_text(encoding="utf-8")
    prompt = (
        "Use the cq-design skill to fulfil this request in the current "
        "directory. Append telemetry per attempt to build/attempts.jsonl as "
        "the skill directs. This is an unattended eval run -- there is no "
        "user to answer clarifying questions. If anything is topology- or "
        "dimension-ambiguous, pick the most common/standard reading, record "
        "the assumption in planning_notes, and proceed without asking.\n\n"
        f"{request}"
    )
    try:
        subprocess.run(
            ["claude", "-p", prompt, "--dangerously-skip-permissions"],
            cwd=case_run_dir,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"  {case}: timed out after {timeout_s}s -- scoring whatever it produced", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, help="run directory (one subdir per case)")
    parser.add_argument("--cases", help="comma-separated case subset (default: all)")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="generate each case via `claude -p` before scoring (costs tokens)",
    )
    parser.add_argument("--generate-timeout", type=int, default=3600)
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    all_cases = sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())
    cases = args.cases.split(",") if args.cases else all_cases
    unknown = sorted(set(cases) - set(all_cases))
    if unknown:
        print(f"unknown cases: {', '.join(unknown)}", file=sys.stderr)
        return 1

    if args.generate:
        for case in cases:
            print(f"generating {case} ...")
            generate_case(case, run_dir, args.generate_timeout)

    prices = load_prices()
    case_results = [score_case(case, run_dir, prices) for case in cases]
    scorecard = {
        "run_dir": str(run_dir),
        "cases": case_results,
        "aggregate": aggregate(case_results),
    }

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "scorecard.json").write_text(
        json.dumps(scorecard, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(scorecard)
    (run_dir / "scorecard.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
