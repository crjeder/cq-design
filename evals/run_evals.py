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

Produced solids are enumerated from the run's `stl/` directory (per
`model_export`'s naming contract, excluding fused `plate_*.stl` and
`keep_out__*.stl`) and matched to golden meshes by a one-to-one geometric
assignment (sorted bbox extents + volume as the cost, solved with
`scipy.optimize.linear_sum_assignment`) -- not by part id, which the golden
and produced plans are never required to agree on. Chamfer is then computed
only for assigned pairs. An unmatched golden part is a miss and fails
`within_tolerance`; a run with no produced solids is reported as a distinct
`no_artifacts` case rather than `unavailable`.

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
from scipy.optimize import linear_sum_assignment

EVALS_DIR = Path(__file__).parent
CASES_DIR = EVALS_DIR / "cases"
PRICES_PATH = EVALS_DIR / "model_prices.json"
CHAMFER_SAMPLES = 2000
CHARS_PER_TOKEN = 4


def load_prices(path: Path = PRICES_PATH) -> dict:
    prices = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in prices.items() if not k.startswith("_")}


def read_recorded_cost(case_run_dir: Path) -> float | None:
    """Billed session cost for a case run, or None to fall back to the estimate.

    Prefers `<case>/cost.json` (the `claude -p` result envelope captured at
    generation), then `<case>/build/cost.json` (the session-cost record's
    `combined` total).
    """
    envelope = case_run_dir / "cost.json"
    if envelope.is_file():
        try:
            data = json.loads(envelope.read_text(encoding="utf-8"))
            if isinstance(data.get("total_cost_usd"), (int, float)):
                return float(data["total_cost_usd"])
        except json.JSONDecodeError:
            pass
    record = case_run_dir / "build" / "cost.json"
    if record.is_file():
        try:
            combined = json.loads(record.read_text(encoding="utf-8")).get("combined", {})
            if isinstance(combined.get("cost_usd"), (int, float)):
                return float(combined["cost_usd"])
        except json.JSONDecodeError:
            pass
    return None


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


def find_produced_stls(case_run_dir: Path) -> list[Path]:
    """Every produced solid in a case run, per `model_export`'s naming contract.

    Excludes fused `plate_*.stl` duplicates (the constituent unions are already
    present individually) and `keep_out__*.stl` (declared keep-out zones, never
    printed geometry). Returns `[]` when `stl/` is absent -- a missing directory
    is "no artifacts", not an error.
    """
    stl_dir = case_run_dir / "stl"
    if not stl_dir.is_dir():
        return []
    return sorted(
        p
        for p in stl_dir.glob("*.stl")
        if not p.name.startswith("plate_") and not p.name.startswith("keep_out__")
    )


def shape_descriptor(mesh: trimesh.Trimesh) -> np.ndarray:
    """Scale-relative shape descriptor: bbox extents sorted descending, plus volume.

    Sorting the extents makes the descriptor invariant to axis-aligned rotation.
    """
    extents = np.sort(mesh.extents)[::-1]
    return np.append(extents, mesh.volume)


def descriptor_cost(a: np.ndarray, b: np.ndarray) -> float:
    """Sum of relative differences per descriptor term, so large and small parts
    contribute comparably instead of the large one dominating."""
    return float(np.sum(np.abs(a - b) / np.maximum(np.maximum(a, b), 1e-9)))


def _input_rate(prices: dict, model: str) -> float:
    return prices.get(model, prices["default"])["input"]


def attempt_metrics(
    attempts: list[dict] | None, prices: dict, recorded_cost: float | None = None
) -> dict:
    """First-shot rate, attempts-to-pass, and cost from one case's telemetry.

    `recorded_cost`, when given, is a billed session cost that replaces the
    `prompt_chars`-derived estimate; `cost_source` reports which was used.
    """
    if attempts is None:
        return {
            "first_shot_rate": None,
            "mean_attempts_to_pass": None,
            "cost_per_accepted_part_usd": None,
            "cost_source": "unavailable",
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
            rate = _input_rate(prices, r.get("model", "default"))
            total_cost += (r["prompt_chars"] / CHARS_PER_TOKEN) * rate / 1e6

    if recorded_cost is not None:
        total_cost = recorded_cost
        cost_source = "recorded"
    else:
        cost_source = "estimate"

    n = len(parts)
    return {
        "first_shot_rate": first_shot / n if n else None,
        "mean_attempts_to_pass": sum(attempts_to_pass) / n if n else None,
        "unpassed_parts": unpassed,
        "cost_per_accepted_part_usd": total_cost / accepted if accepted else None,
        "total_cost_usd": total_cost,
        "cost_source": cost_source,
        "telemetry": "ok",
    }


def score_case(case: str, run_dir: Path, prices: dict) -> dict:
    case_dir = CASES_DIR / case
    plan = json.loads((case_dir / "BUILD_PLAN.json").read_text(encoding="utf-8"))
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    case_run_dir = run_dir / case

    result = {
        "case": case,
        **attempt_metrics(read_attempts(case_run_dir), prices, read_recorded_cost(case_run_dir)),
    }

    golden_ids = [part["id"] for part in plan["parts"]]
    golden_meshes = [load_mesh(case_dir / "golden" / f"{pid}.stl") for pid in golden_ids]
    produced_paths = find_produced_stls(case_run_dir)
    produced_meshes = [load_mesh(p) for p in produced_paths]

    chamfers: dict[str, float | None] = dict.fromkeys(golden_ids)
    matched_to: dict[str, str | None] = dict.fromkeys(golden_ids)

    if produced_meshes:
        golden_descs = [shape_descriptor(m) for m in golden_meshes]
        produced_descs = [shape_descriptor(m) for m in produced_meshes]
        cost = np.array([[descriptor_cost(pd, gd) for gd in golden_descs] for pd in produced_descs])
        row_ind, col_ind = linear_sum_assignment(cost)
        for r, c in zip(row_ind, col_ind, strict=True):
            gid = golden_ids[c]
            chamfers[gid] = chamfer_mm(produced_meshes[r], golden_meshes[c])
            matched_to[gid] = produced_paths[r].name

    measured = [c for c in chamfers.values() if c is not None]
    no_artifacts = len(produced_paths) == 0
    result["no_artifacts"] = no_artifacts
    result["chamfer_mm"] = chamfers
    result["matched_to"] = matched_to
    result["mean_chamfer_mm"] = sum(measured) / len(measured) if measured else None
    result["surplus_produced"] = max(0, len(produced_paths) - meta["expected_parts"])
    result["within_tolerance"] = (
        not no_artifacts
        and all(v is not None for v in chamfers.values())
        and all(c <= meta["tolerance_mm"] for c in measured)
    )
    return result


def aggregate(case_results: list[dict]) -> dict:
    def vals_of(key):
        return [r[key] for r in case_results if r.get(key) is not None]

    def mean_of(key):
        vals = vals_of(key)
        return sum(vals) / len(vals) if vals else None

    chamfer_vals = vals_of("mean_chamfer_mm")
    return {
        "cases_scored": len(case_results),
        "first_shot_rate": mean_of("first_shot_rate"),
        "mean_attempts_to_pass": mean_of("mean_attempts_to_pass"),
        "mean_chamfer_mm": sum(chamfer_vals) / len(chamfer_vals) if chamfer_vals else None,
        "chamfer_cases": len(chamfer_vals),
        "cost_per_accepted_part_usd": mean_of("cost_per_accepted_part_usd"),
    }


def _fmt(value, digits=3) -> str:
    return "unavailable" if value is None else f"{value:.{digits}f}"


def render_markdown(scorecard: dict) -> str:
    lines = [
        "# Eval scorecard",
        "",
        "Cost is billed when `cost src` is `recorded`, otherwise estimated "
        "(tokens ~ prompt_chars / 4, input rate only).",
        "",
        "| case | first-shot | attempts-to-pass | chamfer (mm) | cost/part (USD) | cost src |",
        "|---|---|---|---|---|---|",
    ]
    for r in scorecard["cases"]:
        chamfer_cell = "no artifacts" if r["no_artifacts"] else _fmt(r["mean_chamfer_mm"])
        lines.append(
            f"| {r['case']} | {_fmt(r['first_shot_rate'], 2)} "
            f"| {_fmt(r['mean_attempts_to_pass'], 2)} "
            f"| {chamfer_cell} "
            f"| {_fmt(r['cost_per_accepted_part_usd'], 4)} "
            f"| {r.get('cost_source', 'n/a')} |"
        )
    agg = scorecard["aggregate"]
    lines += [
        "",
        f"**Aggregate** ({agg['cases_scored']} cases): "
        f"first-shot {_fmt(agg['first_shot_rate'], 2)}, "
        f"attempts-to-pass {_fmt(agg['mean_attempts_to_pass'], 2)}, "
        f"chamfer {_fmt(agg['mean_chamfer_mm'])} mm ({agg['chamfer_cases']} cases), "
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
        proc = subprocess.run(
            ["claude", "-p", prompt, "--dangerously-skip-permissions", "--output-format", "json"],
            cwd=case_run_dir,
            timeout=timeout_s,
            check=False,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        print(
            f"  {case}: timed out after {timeout_s}s -- scoring whatever it produced",
            file=sys.stderr,
        )
        return

    try:
        env = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        print(f"  {case}: unparseable `claude -p` JSON -- no cost.json written", file=sys.stderr)
        return
    keys = ("session_id", "num_turns", "duration_ms", "total_cost_usd", "usage")
    cost = {k: env.get(k) for k in keys}
    (case_run_dir / "cost.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")


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
