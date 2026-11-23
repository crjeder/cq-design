"""Run cq-design against the CADGenBench fixtures and package a submission zip.

Developer-only, like `evals/run_evals.py`. CADGenBench's ground truth is private,
so this script only produces candidates; scoring happens on the leaderboard Space
after you upload the zip yourself. Steps, each skipped when its output exists:

1. fetch   the public inputs dataset (HuggingAI4Engineering/cadgenbench-data),
           pinned to the dataset commit it resolves, into --data-dir.
2. generate one unattended `claude -p` cq-design run per fixture (costs tokens) in
           <run>/_work/<id>/ (kept, minus its .venv), then fuses the delivered STEP(s),
           moves the result into the canonical pose (bbox centre at the origin,
           extents Lx >= Ly >= Lz)
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
import re
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
sys.path.insert(0, str(REPO_ROOT / "src"))
import pipeline  # noqa: E402

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
# Pinned: an unpinned `claude -p` took the CLI default, which was Sonnet on
# cgb-104-119-150 and cost fixtures 104/119 their pipeline run (v1 ran Opus).
MODEL = "claude-opus-5-5"
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

# `claude -p` result text when a plan limit is reached ("You've hit your session/weekly limit")
LIMIT_MARKERS = ("session limit", "weekly limit", "usage limit")

UNATTENDED = (
    "This is an unattended benchmark run -- there is no user to answer clarifying "
    "questions. If anything is ambiguous, pick the most standard reading, record the "
    "assumption in planning_notes, and proceed without asking. Append telemetry per "
    "attempt to build/attempts.jsonl as the skill directs."
)
FIDELITY = (
    "This is a CAD-accuracy benchmark, not a print job (profile.json sets design_intent "
    '"cad"): model the nominal geometry exactly, in millimetres, as ONE single solid. '
    "Model every feature and every radius the drawing shows (all views and sections, "
    "including pins, sockets, slots and ribs). Do not add any chamfer or fillet the "
    "drawing does not show, and do not split it into several parts."
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
        # a slash command only expands at the start of the prompt; the rest is its argument
        return (
            "/cq-design:edit input.step "
            + edit.read_text(encoding="utf-8").strip()
            + f"\n\n{UNATTENDED}\n\n{FIDELITY}"
        )
    drawings = ", ".join(sorted(p.name for p in fixture_dir.glob("input*.png")))
    # a slash command only expands at the start of the prompt; the rest is its argument
    return (
        "/cq-design:design Reproduce the part shown in the engineering drawing "
        f"({drawings} in the current directory; read it with the Read tool). The drawing's "
        "dimensions are authoritative. Deliver the STEP format (build/build.py --formats "
        f"step).\n\n{UNATTENDED}\n\n{FIDELITY}"
    )


def audit_pipeline(work: Path) -> dict[str, bool]:
    """Did the fixture's run go through plan, gate and the b1 check? Read from artifacts."""
    done = pipeline.status(work, "design")["done"]
    reports = list((work / "build").glob("*.quality_gate.json"))
    gate_passed = bool(reports) and all(
        json.loads(r.read_text(encoding="utf-8")).get("passed") is True for r in reports
    )
    return {
        "plan": (work / "BUILD_PLAN.json").is_file(),
        "gate_result": "phase3/gate_result" in done,
        "gate_passed": gate_passed,
        "b1_checked": bool(pipeline.approved_b1(work)),
    }


def run_fixture(
    fixture_dir: Path,
    work_dir: Path,
    timeout_s: int,
    plugin_dir: Path | None = None,
    effort: str | None = None,
) -> bool:
    """Run cq-design in work_dir via `claude -p`; return True if it hit a usage limit."""
    shutil.copytree(fixture_dir, work_dir, dirs_exist_ok=True)
    shutil.copyfile(SKILL_CONFIG_SRC, work_dir / "skill_config.json")
    profile = json.loads((REPO_ROOT / "src" / "profile.default.json").read_text(encoding="utf-8"))
    profile["design_intent"] = "cad"
    (work_dir / "profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    cmd = [
        "claude",
        "-p",
        build_prompt(fixture_dir),
        "--model",
        MODEL,
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        *ALLOWED_TOOLS,
    ]
    if plugin_dir:
        cmd += ["--plugin-dir", str(plugin_dir.resolve())]
    if effort:
        cmd += ["--effort", effort]
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
    keys = ("session_id", "num_turns", "duration_ms", "total_cost_usd", "usage", "modelUsage")
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


def pose_step_text(src: Path, out_path: Path) -> None:
    """Write src in the canonical pose by rewriting only its shape representation's placement.

    STEP readers apply that placement as the shape's location, so the B-rep geometry is
    byte-identical to src. A read + OCC re-export instead perturbs it, which on a
    high-tolerance solid can flip the grader's mesh gate (CADGenBench 249).
    """
    bb = cq.importers.importStep(str(src)).findSolid().BoundingBox()
    m = canonical_matrix((bb.center.x, bb.center.y, bb.center.z), (bb.xlen, bb.ylen, bb.zlen))
    text = src.read_text(encoding="utf-8", errors="surrogateescape")
    rep = re.search(r"SHAPE_REPRESENTATION\('[^']*',\((#\d+)", text)
    if rep is None:
        raise ValueError(f"{src}: no shape representation placement")
    place = re.search(
        re.escape(rep.group(1)) + r"\s*=\s*AXIS2_PLACEMENT_3D\('([^']*)',#\d+,#\d+,#\d+\)", text
    )
    if place is None:
        raise ValueError(f"{src}: shape representation item is not an AXIS2_PLACEMENT_3D")
    n = max(int(i) for i in re.findall(r"^#(\d+)\s*=", text, re.M))

    def tup(v: list[float]) -> str:
        return "(" + ",".join(repr(float(x)) for x in v) + ")"

    # fresh entities: the old point/directions may be shared with geometry
    origin, axis, ref = ([m[i][j] for i in range(3)] for j in (3, 2, 0))
    new = (
        f"#{n + 1} = CARTESIAN_POINT('',{tup(origin)});\n"
        f"#{n + 2} = DIRECTION('',{tup(axis)});\n"
        f"#{n + 3} = DIRECTION('',{tup(ref)});\n"
    )
    placement = (
        f"{rep.group(1)} = AXIS2_PLACEMENT_3D('{place.group(1)}',#{n + 1},#{n + 2},#{n + 3})"
    )
    text = text[: place.start()] + placement + text[place.end() :]
    end = text.index("ENDSEC;", text.index("DATA;"))
    out_path.write_text(text[:end] + new + text[end:], encoding="utf-8", errors="surrogateescape")


def step_is_valid(path: Path) -> bool:
    """True when the STEP file re-imports as a valid B-rep."""
    return cq.importers.importStep(str(path)).findSolid().isValid()


def write_candidate(steps: list[Path], out_path: Path) -> None:
    """Pose the delivered STEP canonically (fusing several first) and write output.step."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if len(steps) == 1:
        pose_step_text(steps[0], out_path)
        return
    shapes: list[cq.Shape] = [cq.importers.importStep(str(p)).findSolid() for p in steps]
    fused = functools.reduce(lambda a, b: a.fuse(b), shapes)
    canonical_pose(fused).exportStep(str(out_path))
    if not step_is_valid(out_path):
        print(f"  {out_path.parent.name}: posed solid invalid -- writing unposed", file=sys.stderr)
        fused.exportStep(str(out_path))


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
    run_dir: Path,
    data_dir: Path,
    fixtures: list[str],
    timeout_s: int,
    force: bool,
    plugin_dir: Path | None = None,
    effort: str | None = None,
) -> None:
    """Run cq-design per fixture and write each canonical-pose output.step."""
    for fid in fixtures:
        out = run_dir / fid / "output.step"
        if out.is_file() and not force:
            continue
        work = run_dir / "_work" / fid
        print(f"generating {fid} ...")
        limit_hit = run_fixture(data_dir / fid, work, timeout_s, plugin_dir, effort)
        # keep scripts and logs for diagnosis; the venv is the bulk and is regenerable
        shutil.rmtree(work / ".venv", ignore_errors=True)
        if limit_hit:
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
    parser.add_argument(
        "--plugin-dir", type=Path, help="load cq-design from this checkout (claude --plugin-dir)"
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="claude --effort per fixture run (default: the user's setting)",
    )
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
        generate(
            run_dir, args.data_dir, chosen, args.timeout, args.force, args.plugin_dir, args.effort
        )

    sanity = {}
    for fid in fixtures:
        step = run_dir / fid / "output.step"
        if step.is_file():
            passed, output = sanity_check(args.data_dir, step)
            sanity[fid] = {"passed": passed, "output": output}
            print(f"  {fid}: {'PASS' if passed else 'FAIL'}")
    n_pass = sum(1 for v in sanity.values() if v["passed"])
    n_cand = len(sanity)
    bypassed = []
    for fid in fixtures:
        work = run_dir / "_work" / fid
        if (args.data_dir / fid / "edit_description.txt").is_file() or not work.is_dir():
            continue
        audit = audit_pipeline(work)
        sanity.setdefault(fid, {})["pipeline"] = audit
        if not all(audit.values()):
            bypassed.append(fid)
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
    print(f"{n_cand}/{len(fixtures)} candidates, {n_pass} pass the validity gate")
    if bypassed:
        print(f"pipeline bypassed or incomplete (see sanity.json): {', '.join(bypassed)}")
    print(f"wrote {zip_path} (agree_to_publish=false: set it true in meta.json to submit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
