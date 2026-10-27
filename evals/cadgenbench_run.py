"""Run cq-design against the CADGenBench fixtures and package a submission zip.

Developer-only, like `evals/run_evals.py`. CADGenBench's ground truth is private,
so this script only produces candidates; scoring happens on the leaderboard Space
after you upload the zip yourself. Steps, each skipped when its output exists:

1. fetch   the public inputs dataset (HuggingAI4Engineering/cadgenbench-data),
           pinned to the dataset commit it resolves, into --data-dir.
2. generate one unattended `claude -p` cq-design run per fixture (costs tokens) in
           <run>/_work/<id>/, then fuses the delivered STEP(s), moves the result into
           the canonical pose (bbox centre at the origin, extents Lx >= Ly >= Lz)
           and writes <run>/<id>/output.step. The run gets an explicit tool
           allowlist (ALLOWED_TOOLS), not --dangerously-skip-permissions; a tool
           outside it is denied, not prompted. Generation stops at the first
           usage-limit error; rerun the same command to resume.
3. check   the dataset's `sanity_check_submission.py` validity gate on every
           output.step, in an isolated uv env with the `cadgenbench` package
           (Python 3.12, CADGENBENCH_REF + SANITY_PINS). Results go to <run>/sanity.json.
4. package <run>.zip: meta.json plus one folder per fixture (a fixture with no
           output.step is kept as an empty folder; the Space scores it 0).
           `agree_to_publish` is written false -- the Space rejects that, so set it
           to true yourself only once you decide to publish.

Usage:
    uv run python evals/cadgenbench_run.py --run-dir evals/runs/cgb-v1 \\
        --submitter "Your Name" --name "cq-design v1" [--fixtures 101,201]
"""

from __future__ import annotations

import argparse
import functools
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import cadquery as cq
from OCP.gp import gp_Trsf

EVALS_DIR = Path(__file__).parent
REPO_ROOT = EVALS_DIR.parent
DATA_REPO = "HuggingAI4Engineering/cadgenbench-data"
HF = "https://huggingface.co"
# The commit the leaderboard's grader image installs (CADGENBENCH_SHA=8ae1432 in the
# cadgenbench-eval-gpu Space Dockerfile, 2026-10-19); bump when the Space does.
CADGENBENCH_REF = "8ae143221935ecece1d3d4b5141f3afa4e915988"
# cadgenbench leaves OCP unpinned; OCP 8.0.1.1 (+ build123d 0.13) breaks its STEP load
# (Bnd_Box::Limits binding error), 7.9.3 works. pyvista matches the grader image's pin.
SANITY_PINS = ["cadquery-ocp-novtk<8", "pyvista==0.48.4"]
SANITY_SCRIPT = "sanity_check_submission.py"
SKILL_CONFIG_SRC = (
    REPO_ROOT / "skill_config.json"
    if (REPO_ROOT / "skill_config.json").is_file()
    else REPO_ROOT / "src" / "skill_config.default.json"
)
ALLOWED_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Skill",
    "Agent",
    "Bash(uv:*)",
    "Bash(python:*)",
]

# `claude -p` result text when the plan's limit is reached ("You've hit your session limit")
LIMIT_MARKERS = ("session limit", "usage limit")

UNATTENDED = (
    "This is an unattended benchmark run -- there is no user to answer clarifying "
    "questions. If anything is ambiguous, pick the most standard reading, record the "
    "assumption in planning_notes, and proceed without asking. Append telemetry per "
    "attempt to build/attempts.jsonl as the skill directs."
)
FIDELITY = (
    "This is a CAD-accuracy benchmark, not a print job: model the nominal geometry "
    "exactly, in millimetres, as ONE single solid. Do not add print clearances, "
    "chamfers, fillets, elephant-foot compensation, or split it into several parts. "
    "Deliver the STEP format (build/build.py --formats step)."
)


def fetch_dataset(data_dir: Path) -> str:
    """Download every file of the inputs dataset into data_dir; return the commit sha."""
    with urllib.request.urlopen(f"{HF}/api/datasets/{DATA_REPO}") as resp:
        info = json.load(resp)
    sha = info["sha"]
    for sibling in info["siblings"]:
        rel = sibling["rfilename"]
        dest = data_dir / rel
        if rel.startswith(".") or dest.is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{HF}/datasets/{DATA_REPO}/resolve/{sha}/{rel}"
        with urllib.request.urlopen(url) as resp, dest.open("wb") as out:
            shutil.copyfileobj(resp, out)
    (data_dir / "REVISION").write_text(sha + "\n", encoding="utf-8")
    return sha


def list_fixtures(data_dir: Path) -> list[str]:
    """Fixture ids are the dataset's top-level dirs holding a description.yaml."""
    return sorted(p.parent.name for p in data_dir.glob("*/description.yaml"))


def build_prompt(fixture_dir: Path) -> str:
    """The `claude -p` prompt for one fixture, generation or editing."""
    edit = fixture_dir / "edit_description.txt"
    if edit.is_file():
        task = (
            "Starting solid: input.step in the current directory (renders of it are in "
            "renders/). Import it with cq.importers.importStep and apply this edit, "
            "keeping everything else unchanged and in the same coordinates:\n\n"
            + edit.read_text(encoding="utf-8").strip()
        )
    else:
        drawings = ", ".join(sorted(p.name for p in fixture_dir.glob("input*.png")))
        task = (
            f"Reproduce the part shown in the engineering drawing ({drawings} in the "
            "current directory; read it with the Read tool). The drawing's dimensions "
            "are authoritative."
        )
    return (
        "Use the cq-design skill to fulfil this request in the current directory. "
        f"{UNATTENDED}\n\n{FIDELITY}\n\n{task}"
    )


def run_fixture(fixture_dir: Path, work_dir: Path, timeout_s: int) -> bool:
    """Run cq-design in work_dir via `claude -p`; return True if it hit a usage limit."""
    shutil.copytree(fixture_dir, work_dir, dirs_exist_ok=True)
    shutil.copyfile(SKILL_CONFIG_SRC, work_dir / "skill_config.json")
    cmd = [
        "claude",
        "-p",
        build_prompt(fixture_dir),
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        *ALLOWED_TOOLS,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=work_dir, timeout=timeout_s, check=False, capture_output=True, text=True
        )
    except subprocess.TimeoutExpired:
        print(f"  {fixture_dir.name}: timed out after {timeout_s}s", file=sys.stderr)
        return False
    try:
        env = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        print(f"  {fixture_dir.name}: unparseable `claude -p` JSON", file=sys.stderr)
        return False
    if env.get("is_error"):
        result = str(env.get("result"))
        print(f"  {fixture_dir.name}: `claude -p` error: {result}", file=sys.stderr)
        if any(m in result for m in LIMIT_MARKERS):
            return True
    keys = ("session_id", "num_turns", "duration_ms", "total_cost_usd", "usage")
    cost = {k: env.get(k) for k in keys}
    (work_dir / "cost.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    return False


def delivered_steps(work_dir: Path) -> list[Path]:
    """STEP files the run delivered: out/ first, else build/ (never the input)."""
    for sub in ("out", "build"):
        found = sorted((work_dir / sub).glob("*.st*p"))
        if found:
            return found
    return []


def canonical_matrix(center: tuple, extents: tuple) -> list[list[float]]:
    """4x4 rigid transform taking center to 0 and the longest..shortest extent to X, Y, Z."""
    order = sorted(range(3), key=lambda i: -extents[i])
    rot = [[1.0 if j == order[i] else 0.0 for j in range(3)] for i in range(3)]
    # an odd permutation matrix is a reflection; flip Z to keep it a rotation
    odd = sum(order[i] > order[j] for i in range(3) for j in range(i + 1, 3)) % 2
    if odd:
        rot[2] = [-v for v in rot[2]]
    rows = [r + [-sum(r[j] * center[j] for j in range(3))] for r in rot]
    return [*rows, [0.0, 0.0, 0.0, 1.0]]


def canonical_pose(shape: cq.Shape) -> cq.Shape:
    """Rotate/translate shape so its bbox is centred at 0 with extents Lx >= Ly >= Lz."""
    bb = shape.BoundingBox()
    center = (bb.center.x, bb.center.y, bb.center.z)
    rows = canonical_matrix(center, (bb.xlen, bb.ylen, bb.zlen))[:3]
    trsf = gp_Trsf()
    trsf.SetValues(*(v for row in rows for v in row))
    return shape.transformShape(cq.Matrix(trsf))


def write_candidate(steps: list[Path], out_path: Path) -> None:
    """Fuse the delivered STEP(s), pose canonically, and export output.step."""
    shapes: list[cq.Shape] = [cq.importers.importStep(str(p)).findSolid() for p in steps]
    fused = functools.reduce(lambda a, b: a.fuse(b), shapes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_pose(fused).exportStep(str(out_path))


def sanity_check(data_dir: Path, step: Path) -> tuple[bool, str]:
    """Run the dataset's validity gate on one candidate; return (passed, output)."""
    pkg = f"cadgenbench @ git+https://github.com/huggingface/cadgenbench@{CADGENBENCH_REF}"
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            "--python",
            "3.12",
            "--with",
            pkg,
            *(arg for pin in SANITY_PINS for arg in ("--with", pin)),
            "python",
            "-I",
            str((data_dir / SANITY_SCRIPT).resolve()),
            str(step.resolve()),
        ],
        cwd=step.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def package(run_dir: Path, fixtures: list[str], meta: dict) -> Path:
    """Write <run_dir>.zip: meta.json plus one folder per fixture."""
    zip_path = run_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("meta.json", json.dumps(meta, indent=2) + "\n")
        for fid in fixtures:
            zf.writestr(f"{fid}/", "")
            step = run_dir / fid / "output.step"
            if step.is_file():
                zf.write(step, f"{fid}/output.step")
    return zip_path


def generate(
    run_dir: Path, data_dir: Path, fixtures: list[str], timeout_s: int, force: bool
) -> None:
    """Run cq-design per fixture and write each canonical-pose output.step."""
    for fid in fixtures:
        out = run_dir / fid / "output.step"
        if out.is_file() and not force:
            continue
        work = run_dir / "_work" / fid
        print(f"generating {fid} ...")
        if run_fixture(data_dir / fid, work, timeout_s):
            print(f"  usage limit hit at {fid}: stopping; rerun to resume", file=sys.stderr)
            return
        steps = delivered_steps(work)
        if not steps:
            print(f"  {fid}: no STEP delivered -- left missing", file=sys.stderr)
            continue
        try:
            write_candidate(steps, out)
        except Exception as exc:  # one broken delivery must not stop the other fixtures
            print(f"  {fid}: could not write output.step: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--data-dir", type=Path, default=EVALS_DIR / "runs" / "cadgenbench-data")
    parser.add_argument("--fixtures", help="comma-separated subset to generate (default: all)")
    parser.add_argument("--timeout", type=int, default=3600, help="per-fixture timeout (s)")
    parser.add_argument("--force", action="store_true", help="regenerate existing output.step")
    parser.add_argument("--skip-generate", action="store_true", help="only check + package")
    parser.add_argument("--submitter", required=True, help="meta.json submitter_name")
    parser.add_argument("--name", required=True, help="meta.json submission_name")
    parser.add_argument("--agent-url", default="https://github.com/crjeder/cq-design")
    parser.add_argument("--notes", default=None)
    args = parser.parse_args(argv)

    sha = fetch_dataset(args.data_dir)
    fixtures = list_fixtures(args.data_dir)
    print(f"dataset {DATA_REPO}@{sha[:12]}: {len(fixtures)} fixtures")
    chosen = args.fixtures.split(",") if args.fixtures else fixtures
    unknown = sorted(set(chosen) - set(fixtures))
    if unknown:
        print(f"unknown fixtures: {', '.join(unknown)}", file=sys.stderr)
        return 1

    run_dir: Path = args.run_dir
    if not args.skip_generate:
        generate(run_dir, args.data_dir, chosen, args.timeout, args.force)

    sanity = {}
    for fid in fixtures:
        step = run_dir / fid / "output.step"
        if step.is_file():
            passed, output = sanity_check(args.data_dir, step)
            sanity[fid] = {"passed": passed, "output": output}
            print(f"  {fid}: {'PASS' if passed else 'FAIL'}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "sanity.json").write_text(json.dumps(sanity, indent=2) + "\n", encoding="utf-8")

    meta = {
        "submitter_name": args.submitter,
        "submission_name": args.name,
        "agent_url": args.agent_url,
        "notes": args.notes,
        "agree_to_publish": False,
    }
    zip_path = package(run_dir, fixtures, meta)
    n_pass = sum(1 for v in sanity.values() if v["passed"])
    print(f"{len(sanity)}/{len(fixtures)} candidates, {n_pass} pass the validity gate")
    print(f"wrote {zip_path} (agree_to_publish=false: set it true in meta.json to submit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
