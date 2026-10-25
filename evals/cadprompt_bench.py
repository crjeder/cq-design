"""External benchmark: score cq-design part scripts against CADPrompt ground truth.

CADPrompt (github.com/Kamel773/CAD_Code_Generation, arXiv 2410.05340) ships 200
prompts with DeepCAD ground-truth meshes. The upstream repo declares no license, so
nothing from it is committed here: pass a local, manually-downloaded copy of its
`CADPrompt/` folder via --dataset. Run with `python -I` since the dataset is
untrusted data (this script only parses its STL files, never executes them).

For each selected prompt id, `evals/cadprompt/parts/p<id>.py` (authored from the
prompt's `..._with_specific_measurements.txt` text) is delivered through
`run_cadquery_model.py --deliver --formats stl`, then scored against
`<dataset>/<id>/Ground_Truth.stl` following the paper: both meshes are normalized
to a unit cube (bbox-centered, scaled by the largest extent), the produced mesh is
rigidly ICP-aligned onto the ground truth (seeded from all 24 axis-aligned
rotations, since a build pose need not match the DeepCAD frame), then Chamfer
distance (symmetric mean nearest-neighbour over sampled surface points) and
volumetric IoU (inside-test on a regular grid) are computed. A part that
fails to build scores Chamfer sqrt(3), IoU 0.

Usage:
    uv run python -I evals/cadprompt_bench.py --dataset /path/to/CADPrompt --out /tmp/run
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

EVALS_DIR = Path(__file__).resolve().parent
PARTS_DIR = EVALS_DIR / "cadprompt" / "parts"
RUNNER = EVALS_DIR.parent / "src" / "run_cadquery_model.py"

# id -> CADPrompt "Semantic complexity" tier (Data_Stratification.xlsx).
SELECTION = {
    "00003558": "Simple",
    "00009823": "Simple",
    "00670106": "Simple",
    "00000633": "Moderate",
    "00004154": "Moderate",
    "00996329": "Moderate",
    "00001817": "Complex",
    "00520321": "Complex",
    "00037135": "Very Complex",
    "00039681": "Very Complex",
}
TIERS = ["Simple", "Moderate", "Complex", "Very Complex"]

SAMPLES = 2048
GRID = 48
SEED = 0
FAIL_CHAMFER = float(np.sqrt(3.0))


def normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Center on the bbox center and scale the largest extent to 1."""
    mesh = mesh.copy()
    mesh.apply_translation(-mesh.bounds.mean(axis=0))
    mesh.apply_scale(1.0 / float(mesh.extents.max()))
    return mesh


def cube_rotations() -> list[np.ndarray]:
    """The 24 proper rotations mapping axes onto axes, as 4x4 transforms."""
    mats = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            rot = np.zeros((3, 3))
            rot[range(3), perm] = signs
            if np.isclose(np.linalg.det(rot), 1.0):
                mat = np.eye(4)
                mat[:3, :3] = rot
                mats.append(mat)
    return mats


def align(produced: trimesh.Trimesh, golden: trimesh.Trimesh) -> trimesh.Trimesh:
    """Rigid ICP of the produced mesh onto the golden one (no scale, no reflection).

    The paper runs ICP from identity; part scripts here are authored in their own
    build pose, so ICP is seeded from each of the 24 axis-aligned rotations and the
    lowest-cost result kept.
    """
    pts = trimesh.sample.sample_surface(produced, SAMPLES, seed=SEED)[0]
    best = min(
        (
            trimesh.registration.icp(
                pts, golden, initial=seed, max_iterations=50, reflection=False, scale=False
            )
            for seed in cube_rotations()
        ),
        key=lambda result: result[2],
    )
    aligned = produced.copy()
    aligned.apply_transform(best[0])
    return aligned


def chamfer(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    pa = trimesh.sample.sample_surface(a, SAMPLES, seed=SEED)[0]
    pb = trimesh.sample.sample_surface(b, SAMPLES, seed=SEED + 1)[0]
    d_ab = cKDTree(pb).query(pa)[0]
    d_ba = cKDTree(pa).query(pb)[0]
    return float((d_ab.mean() + d_ba.mean()) / 2.0)


def volume_iou(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    lo = np.minimum(a.bounds[0], b.bounds[0])
    hi = np.maximum(a.bounds[1], b.bounds[1])
    axes = [np.linspace(lo[i], hi[i], GRID) for i in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    in_a, in_b = a.contains(grid), b.contains(grid)
    union = np.count_nonzero(in_a | in_b)
    return float(np.count_nonzero(in_a & in_b) / union) if union else 0.0


def score_pair(produced_stl: Path, golden_stl: Path) -> dict:
    golden = normalize(trimesh.load(golden_stl, force="mesh"))
    produced = align(normalize(trimesh.load(produced_stl, force="mesh")), golden)
    return {"chamfer": chamfer(produced, golden), "iou": volume_iou(produced, golden)}


def deliver(part_id: str, out_dir: Path) -> Path | None:
    """Run the part loop's deliver step; return the produced STL or None on failure."""
    script = PARTS_DIR / f"p{part_id}.py"
    if not script.exists():
        return None
    proc = subprocess.run(
        [sys.executable, str(RUNNER), str(script), "--deliver", "--formats", "stl",
         "--output-dir", str(out_dir / part_id)],
        capture_output=True, text=True,
    )  # fmt: skip
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return Path(report["stl"]) if report.get("success") and report.get("stl") else None


def run(dataset: Path, out_dir: Path) -> list[dict]:
    rows = []
    for part_id, tier in SELECTION.items():
        stl = deliver(part_id, out_dir)
        row = {"id": part_id, "tier": tier, "built": stl is not None}
        if stl is None:
            row.update(chamfer=FAIL_CHAMFER, iou=0.0)
        else:
            row.update(score_pair(stl, dataset / part_id / "Ground_Truth.stl"))
        rows.append(row)
    return rows


def render(rows: list[dict]) -> str:
    lines = ["| id | tier | built | chamfer | iou |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['tier']} | {'yes' if r['built'] else 'no'} "
            f"| {r['chamfer']:.4f} | {r['iou']:.3f} |"
        )
    groups = [(t, [r for r in rows if r["tier"] == t]) for t in TIERS] + [("all", rows)]
    for name, group in groups:
        if group:
            ch = np.mean([r["chamfer"] for r in group])
            iou = np.mean([r["iou"] for r in group])
            lines.append(f"| **mean** | {name} | {sum(r['built'] for r in group)}/{len(group)} "
                         f"| {ch:.4f} | {iou:.3f} |")  # fmt: skip
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", type=Path, required=True, help="Local CADPrompt/ folder")
    parser.add_argument("--out", type=Path, required=True, help="Run dir for delivered STLs")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = run(args.dataset, args.out)
    (args.out / "cadprompt_scores.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
