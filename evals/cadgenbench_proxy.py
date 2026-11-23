"""Score a CADGenBench run locally against a proxy ground truth.

Developer-only. The real ground truth is private, but the leaderboard's submissions
dataset (HuggingAI4Engineering/cadgenbench-submissions, CC-BY-4.0) publishes every
uploaded zip plus its per-fixture `cad_score` against that ground truth. Per fixture,
the highest-scoring published candidate becomes the proxy ground truth, and
`cadgenbench evaluate` (the grader's own code, CADGENBENCH_REF) scores the run
against it. Never give the proxy files to a generation run: they are a grading aid.

Not the leaderboard number:
- the proxy is itself off by (1 - proxy score); trust fixtures above --min-proxy only;
- the interface axis needs the private jig sub-volumes, so it is absent and the
  CAD score renormalizes over shape + topology;
- editing fixtures get an `edit_baseline.json` computed from input.step vs the proxy;
  their renormalized shape axis amplifies proxy error, so only the generation mean
  tracks the leaderboard (calibrated r 0.86 generation, 0.70 editing).

Steps (cached under --gt-dir; a fixture's proxy is re-fetched when its pick changes):
1. read results.jsonl, keep completed rows on the current dataset revision, drop
   --exclude matches, pick the best valid candidate per fixture -> <gt>/proxy.json;
2. download only the zips holding a pick, copy each pick to <gt>/gt/<id>/ground_truth.step;
3. copy <run>/<id>/output.step into <run>/_proxy/<id>/ and run `cadgenbench evaluate`;
4. write <run>/proxy_scores.json and print a markdown table. --compare <submission id>
   adds that submission's leaderboard score per fixture (calibration).

Usage:
    uv run python evals/cadgenbench_proxy.py --run-dir evals/runs/cgb-v1
    # calibrate: score our own leaderboard zip without letting it be its own proxy
    uv run python evals/cadgenbench_proxy.py --run-dir evals/runs/cgb-final \\
        --exclude crjeder_ --compare crjeder_cq-design-v0-1-0-merged-best-of_20261121-150706
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from cadgenbench_run import CADGENBENCH_REF, EVALS_DIR, HF, SANITY_PINS, fetch_dataset

SUBMISSIONS_REPO = "HuggingAI4Engineering/cadgenbench-submissions"
RESULTS_URL = f"{HF}/datasets/{SUBMISSIONS_REPO}/resolve/main/results.jsonl"
BASELINE_CODE = (
    "import sys; from cadgenbench.eval.edit_baseline import compute_edit_baseline, "
    "write_edit_baseline; write_edit_baseline(sys.argv[2], "
    "compute_edit_baseline(sys.argv[1], sys.argv[2] + '/ground_truth.step'))"
)


def load_results() -> list[dict]:
    """Every row of the leaderboard's results.jsonl."""
    with urllib.request.urlopen(RESULTS_URL) as resp:
        return [json.loads(line) for line in resp.read().decode("utf-8").splitlines() if line]


def pick_proxies(rows: list[dict], revision: str, exclude: list[str]) -> dict[str, dict]:
    """Best valid candidate per fixture among completed rows on this dataset revision."""
    best: dict[str, dict] = {}
    for row in rows:
        if row.get("status") != "completed" or not revision.startswith(
            row.get("cadgenbench_data_revision") or "-"
        ):
            continue
        if any(x in row["submission_id"] for x in exclude):
            continue
        for fid, s in (row.get("per_sample_scores") or {}).items():
            score = s.get("cad_score")
            if s.get("status") != "valid" or score is None:
                continue
            key = (score, row.get("aggregate_score") or 0.0)
            if fid not in best or key > best[fid]["_key"]:
                best[fid] = {
                    "_key": key,
                    "submission_id": row["submission_id"],
                    "submission_name": row["submission_name"],
                    "submitter_name": row["submitter_name"],
                    "cad_score": score,
                    "url": row["submission_blob_url"],
                }
    for v in best.values():
        del v["_key"]
    return best


def zip_member(zf: zipfile.ZipFile, fid: str) -> str | None:
    """The zip entry holding fixture fid's candidate (read only; never extracted by name)."""
    for name in zf.namelist():
        parts = name.split("/")
        if len(parts) >= 2 and parts[-2] == fid and parts[-1] in ("output.step", "output.stp"):
            return name
    return None


def cadgenbench_cmd(*args: str) -> list[str]:
    """`uv run` in an isolated env with the grader's cadgenbench commit."""
    pkg = f"cadgenbench @ git+https://github.com/huggingface/cadgenbench@{CADGENBENCH_REF}"
    pins = [arg for pin in SANITY_PINS for arg in ("--with", pin)]
    return [
        "uv",
        "run",
        "--no-project",
        "--isolated",
        "--python",
        "3.12",
        "--with",
        pkg,
        *pins,
        *args,
    ]


def is_editing(data_dir: Path, fid: str) -> bool:
    """An editing fixture ships an edit_description.txt (same rule as cadgenbench_run)."""
    return (data_dir / fid / "edit_description.txt").is_file()


def build_gt(gt_dir: Path, data_dir: Path, picks: dict[str, dict]) -> None:
    """Materialise <gt>/gt/<id>/ground_truth.step (+ edit_baseline.json) for every pick."""
    proxy_json = gt_dir / "proxy.json"
    old = json.loads(proxy_json.read_text(encoding="utf-8")) if proxy_json.is_file() else {}
    zips = gt_dir / "_zips"
    zips.mkdir(parents=True, exist_ok=True)
    for fid, pick in sorted(picks.items()):
        if is_editing(data_dir, fid):
            # the grader's edit-diff render reads the input from <data>/inputs/<id>/
            (gt_dir / "inputs" / fid).mkdir(parents=True, exist_ok=True)
            for name in ("input.step", "input.mesh.npz"):
                if (data_dir / fid / name).is_file():
                    shutil.copyfile(data_dir / fid / name, gt_dir / "inputs" / fid / name)
        dest = gt_dir / "gt" / fid
        if (
            old.get(fid, {}).get("submission_id") == pick["submission_id"]
            and (dest / "ground_truth.step").is_file()
        ):
            continue
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        zpath = zips / f"{pick['submission_id']}.zip"
        if not zpath.is_file():
            print(f"downloading {pick['submission_id']} ...")
            with urllib.request.urlopen(pick["url"]) as resp, zpath.open("wb") as out:
                shutil.copyfileobj(resp, out)
        with zipfile.ZipFile(zpath) as zf:
            member = zip_member(zf, fid)
            if member is None:
                raise RuntimeError(f"{zpath.name} has no candidate for fixture {fid}")
            (dest / "ground_truth.step").write_bytes(zf.read(member))
        input_step = data_dir / fid / "input.step"
        if is_editing(data_dir, fid) and input_step.is_file():
            cmd = cadgenbench_cmd(
                "python", "-I", "-c", BASELINE_CODE, str(input_step.resolve()), str(dest.resolve())
            )
            subprocess.run(cmd, check=True)
    proxy_json.write_text(json.dumps(picks, indent=2) + "\n", encoding="utf-8")


def evaluate(run_dir: Path, gt_dir: Path, fixtures: list[str], workers: int) -> Path:
    """Copy candidates into <run>/_proxy/ and run `cadgenbench evaluate` on them."""
    score_dir = run_dir / "_proxy"
    for fid in fixtures:
        dest = score_dir / fid
        dest.mkdir(parents=True, exist_ok=True)
        src = run_dir / fid / "output.step"
        if src.is_file():
            shutil.copyfile(src, dest / "output.step")
        else:
            (dest / "output.step").unlink(missing_ok=True)
    env = {**os.environ, "CADGENBENCH_DATA_DIR": str(gt_dir.resolve())}
    env.pop("CADGENBENCH_DATA_GT_REPO", None)
    cmd = cadgenbench_cmd(
        "cadgenbench", "evaluate", str(score_dir.resolve()), "--workers", str(workers)
    )
    subprocess.run(cmd, check=False, env=env)
    return score_dir


def collect(
    score_dir: Path, data_dir: Path, picks: dict[str, dict], compare: dict | None
) -> list[dict]:
    """One row per fixture from each result.json."""
    out = []
    for fid in sorted(picks):
        path = score_dir / fid / "result.json"
        res = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        row = {
            "id": fid,
            "task": "editing" if is_editing(data_dir, fid) else "generation",
            "proxy_score": picks[fid]["cad_score"],
            "status": res.get("status", "error"),
            "cad_score": res.get("cad_score"),
            "shape": (res.get("gt_metrics") or {}).get("shape_similarity_score"),
            "topology": (res.get("topology_metrics") or {}).get("score"),
        }
        if compare is not None:
            row["leaderboard"] = (compare.get(fid) or {}).get("cad_score")
        out.append(row)
    return out


def fmt(v: float | None) -> str:
    return "-" if v is None else f"{v:.3f}"


def report(rows: list[dict], min_proxy: float) -> str:
    """Markdown table plus all-fixture and trusted-fixture means."""
    has_lb = rows and "leaderboard" in rows[0]
    head = "| id | proxy | status | cad | shape | topo |" + (" leaderboard |" if has_lb else "")
    lines = [head, "|" + "---|" * (head.count("|") - 1)]
    for r in rows:
        cells = [
            r["id"],
            fmt(r["proxy_score"]),
            r["status"],
            fmt(r["cad_score"]),
            fmt(r["shape"]),
            fmt(r["topology"]),
        ]
        if has_lb:
            cells.append(fmt(r["leaderboard"]))
        lines.append("| " + " | ".join(cells) + " |")
    groups = [("all", rows)]
    for task in ("generation", "editing"):
        of_task = [r for r in rows if r["task"] == task]
        trusted = [r for r in of_task if r["proxy_score"] >= min_proxy]
        groups += [(task, of_task), (f"{task}, proxy >= {min_proxy}", trusted)]
    for label, sel in groups:
        scores = [r["cad_score"] or 0.0 for r in sel]
        line = f"\nmean cad ({label}, n={len(sel)}): {statistics.fmean(scores):.4f}" if sel else ""
        if has_lb and sel:
            lb = [r["leaderboard"] or 0.0 for r in sel]
            diffs = [abs(a - b) for a, b in zip(scores, lb, strict=True)]
            corr = (
                statistics.correlation(scores, lb)
                if len(sel) > 1 and len(set(lb)) > 1
                else float("nan")
            )
            line += f", leaderboard {statistics.fmean(lb):.4f}"
            line += f", mean |diff| {statistics.fmean(diffs):.4f}, r {corr:.3f}"
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--data-dir", type=Path, default=EVALS_DIR / "runs" / "cadgenbench-data")
    parser.add_argument("--gt-dir", type=Path, default=EVALS_DIR / "runs" / "cadgenbench-proxy-gt")
    parser.add_argument(
        "--exclude", action="append", default=[], help="drop submission ids containing this"
    )
    parser.add_argument(
        "--compare", help="submission id whose leaderboard scores to show beside ours"
    )
    parser.add_argument(
        "--min-proxy", type=float, default=0.95, help="proxy score for the trusted mean"
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    revision = fetch_dataset(args.data_dir)
    rows = load_results()
    picks = pick_proxies(rows, revision, args.exclude)
    compare = None
    if args.compare:
        match = [r for r in rows if r["submission_id"] == args.compare]
        if not match:
            print(f"no submission {args.compare!r} in results.jsonl", file=sys.stderr)
            return 1
        compare = match[0]["per_sample_scores"]
    n_zips = len({p["submission_id"] for p in picks.values()})
    print(f"{len(picks)} fixtures with a proxy from {n_zips} submissions")
    build_gt(args.gt_dir, args.data_dir, picks)
    score_dir = evaluate(args.run_dir, args.gt_dir, sorted(picks), args.workers)
    results = collect(score_dir, args.data_dir, picks, compare)
    (args.run_dir / "proxy_scores.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    print(report(results, args.min_proxy))
    return 0


if __name__ == "__main__":
    sys.exit(main())
